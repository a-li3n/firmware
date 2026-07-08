/\*----------------------------------------------------------------------------/
 Lovyan GFX - Graphics library for embedded devices.

Original Source:
 https://github.com/lovyan03/LovyanGFX/

Licence:
 \[FreeBSD\](https://github.com/lovyan03/LovyanGFX/blob/master/license.txt)

Author:
 \[lovyan03\](https://twitter.com/lovyan03)

Contributors:
 \[ciniml\](https://github.com/ciniml)
 \[mongonta0716\](https://github.com/mongonta0716)
 \[tobozo\](https://github.com/tobozo)
/----------------------------------------------------------------------------\*/

#include "Panel\_FrameBufferBase.hpp"
#include "../platforms/common.hpp"
#include "../misc/pixelcopy.hpp"
#include "../misc/common\_function.hpp"

#if defined (ESP\_PLATFORM)
 #include

 #if \_\_has\_include()
 #include
 #endif
 #if defined (ESP\_CACHE\_MSYNC\_FLAG\_DIR\_C2M)
 \_\_attribute\_\_((weak))
 int Cache\_WriteBack\_Addr(uint32\_t addr, uint32\_t size)
 {
 uintptr\_t start = addr & ~127u;
 uintptr\_t end = (addr + size + 127u) & ~127u;
 if (start >= end) return 0;
 return esp\_cache\_msync((void\*)start, end - start, ESP\_CACHE\_MSYNC\_FLAG\_DIR\_C2M \| ESP\_CACHE\_MSYNC\_FLAG\_TYPE\_DATA);
 // auto res = esp\_cache\_msync((void\*)start, end - start, ESP\_CACHE\_MSYNC\_FLAG\_DIR\_C2M \| ESP\_CACHE\_MSYNC\_FLAG\_TYPE\_DATA);
 // if (res != ESP\_OK){
 // printf("start: %08x, end: %08x\\n", start, end);
 // }
 // return res;
 }
 #define LGFX\_USE\_CACHE\_WRITEBACK\_ADDR
 #else
 #if defined (CONFIG\_IDF\_TARGET\_ESP32S3)
 #if \_\_has\_include()
 #include
 extern int Cache\_WriteBack\_Addr(uint32\_t addr, uint32\_t size);
 #define LGFX\_USE\_CACHE\_WRITEBACK\_ADDR
 #endif
 #endif
 #endif
#endif

namespace lgfx
{
 inline namespace v1
 {
//----------------------------------------------------------------------------

#if defined ( LGFX\_USE\_CACHE\_WRITEBACK\_ADDR )
 void cacheWriteBack(const void\* ptr, uint32\_t size)
 {
 if (!isEmbeddedMemory(ptr))
 {
 Cache\_WriteBack\_Addr((uint32\_t)ptr, size);
 }
 }
#else
 static inline void cacheWriteBack(const void\*, uint32\_t) {}
#endif

 bool Panel\_FrameBufferBase::init(bool use\_reset)
 {
#if defined ( LGFX\_USE\_CACHE\_WRITEBACK\_ADDR )
 // キャッシュのライトバックを display メソッドで行うため、auto\_displayで自動化する
 \_auto\_display = true;
#endif
 \_range\_mod.top = INT16\_MAX;
 \_range\_mod.left = INT16\_MAX;
 \_range\_mod.right = 0;
 \_range\_mod.bottom = 0;

 setInvert(\_invert);
 setRotation(\_rotation);

 if (!Panel\_Device::init(use\_reset))
 {
 return false;
 }
 return true;
 }

 void Panel\_FrameBufferBase::setRotation(uint\_fast8\_t r)
 {
 r &= 7;
 \_rotation = r;
 \_internal\_rotation = ((r + \_cfg.offset\_rotation) & 3) \| ((r & 4) ^ (\_cfg.offset\_rotation & 4));

 auto pw = \_cfg.panel\_width;
 auto ph = \_cfg.panel\_height;
 if (\_internal\_rotation & 1)
 {
 std::swap(pw, ph);
 }
 \_width = pw;
 \_height = ph;
 \_xe = pw-1;
 \_ye = ph-1;
 \_xs = 0;
 \_ys = 0;
 }

 void Panel\_FrameBufferBase::display(uint\_fast16\_t x, uint\_fast16\_t y, uint\_fast16\_t w, uint\_fast16\_t h)
 {
 if (0 < w && 0 < h)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 if (r)
 {
 if ((1u << r) & 0b10010110) { y = \_height - (y + h); }
 if (r & 2) { x = \_width - (x + w); }
 if (r & 1) { std::swap(x, y); std::swap(w, h); }
 }
 \_range\_mod.left = std::min(\_range\_mod.left , x );
 \_range\_mod.right = std::max(\_range\_mod.right , x + w - 1);
 \_range\_mod.top = std::min(\_range\_mod.top , y );
 \_range\_mod.bottom = std::max(\_range\_mod.bottom, y + h - 1);
 }
 if (\_range\_mod.empty()) { return; }
#if defined ( LGFX\_USE\_CACHE\_WRITEBACK\_ADDR )
 int ye = \_range\_mod.bottom + 1;
 int xs\_byte = \_range\_mod.left \* \_write\_bits >> 3;
 int xe\_byte = (\_range\_mod.right+1) \* \_write\_bits >> 3;
 size\_t bytes = xe\_byte - xs\_byte;

 void\* ptr\_start = (void\*)~0;
 void\* ptr\_end = nullptr;
 for (int y = \_range\_mod.top; y < ye; ++y)
 {
 auto ptr = &\_lines\_buffer\[y\]\[xs\_byte\];
 if (!isEmbeddedMemory(ptr))
 {
 if (ptr\_start < ptr\_end) {
 // 4096byte以上離れている場合はライトバック
 if ((ptr + bytes + 4096 < ptr\_start)
 \|\| (ptr - 4096 > ptr\_end)) {
 cacheWriteBack(ptr\_start, (int)ptr\_end - (int)ptr\_start);
 ptr\_start = ptr;
 ptr\_end = ptr + bytes;
 }
 }
 if (ptr\_start > ptr) {
 ptr\_start = ptr;
 }
 if (ptr\_end < (ptr + bytes)) {
 ptr\_end = (ptr + bytes);
 }
 }
 }
 if (ptr\_start < ptr\_end) {
 cacheWriteBack(ptr\_start, (int)ptr\_end - (int)ptr\_start);
 }
#endif
 \_range\_mod.top = INT16\_MAX;
 \_range\_mod.left = INT16\_MAX;
 \_range\_mod.right = 0;
 \_range\_mod.bottom = 0;
 }

 void Panel\_FrameBufferBase::setWindow(uint\_fast16\_t xs, uint\_fast16\_t ys, uint\_fast16\_t xe, uint\_fast16\_t ye)
 {
 xs = std::max(0u, std::min(\_width - 1, xs));
 xe = std::max(0u, std::min(\_width - 1, xe));
 ys = std::max(0u, std::min(\_height - 1, ys));
 ye = std::max(0u, std::min(\_height - 1, ye));
 \_xpos = xs;
 \_xs = xs;
 \_xe = xe;
 \_ypos = ys;
 \_ys = ys;
 \_ye = ye;
 }

 void Panel\_FrameBufferBase::drawPixelPreclipped(uint\_fast16\_t x, uint\_fast16\_t y, uint32\_t rawcolor)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 if (r)
 {
 if ((1u << r) & 0b10010110) { y = \_height - (y + 1); }
 if (r & 2) { x = \_width - (x + 1); }
 if (r & 1) { std::swap(x, y); }
 }
 if (\_write\_bits >= 8)
 {
 \_range\_mod.left = std::min(\_range\_mod.left , x);
 \_range\_mod.right = std::max(\_range\_mod.right , x);
 \_range\_mod.top = std::min(\_range\_mod.top , y);
 \_range\_mod.bottom = std::max(\_range\_mod.bottom, y);

 size\_t bytes = \_write\_bits >> 3;
 auto ptr = &\_lines\_buffer\[y\]\[x \* bytes\];
 memcpy(ptr, &rawcolor, bytes);
 // cacheWriteBack(ptr, bytes);
 }
 }

 void Panel\_FrameBufferBase::writeFillRectPreclipped(uint\_fast16\_t x, uint\_fast16\_t y, uint\_fast16\_t w, uint\_fast16\_t h, uint32\_t rawcolor)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 if (r)
 {
 if ((1u << r) & 0b10010110) { y = \_height - (y + h); }
 if (r & 2) { x = \_width - (x + w); }
 if (r & 1) { std::swap(x, y); std::swap(w, h); }
 }
 \_range\_mod.left = std::min(\_range\_mod.left , x );
 \_range\_mod.right = std::max(\_range\_mod.right , x + w - 1);
 \_range\_mod.top = std::min(\_range\_mod.top , y );
 \_range\_mod.bottom = std::max(\_range\_mod.bottom, y + h - 1);

 h += y;
 if (\_write\_bits >= 8)
 {
 size\_t bytes = \_write\_bits >> 3;
 do
 {
 auto ptr = &\_lines\_buffer\[y\]\[x \* bytes\];
 memset\_multi(ptr, rawcolor, bytes, w);
 // cacheWriteBack(ptr, bytes \* w);
 } while (++y < h);
 }
 }

 void Panel\_FrameBufferBase::writeBlock(uint32\_t rawcolor, uint32\_t length)
 {
 do
 {
 uint32\_t h = 1;
 auto w = std::min(length, \_xe + 1 - \_xpos);
 if (length >= (w << 1) && \_xpos == \_xs)
 {
 h = std::min(length / w, \_ye + 1 - \_ypos);
 }
 writeFillRectPreclipped(\_xpos, \_ypos, w, h, rawcolor);
 if ((\_xpos += w) <= \_xe) return;
 \_xpos = \_xs;
 if (\_ye < (\_ypos += h)) { \_ypos = \_ys; }
 length -= w \* h;
 } while (length);
 }

 void Panel\_FrameBufferBase::\_rotate\_pixelcopy(uint\_fast16\_t& x, uint\_fast16\_t& y, uint\_fast16\_t& w, uint\_fast16\_t& h, pixelcopy\_t\* param, uint32\_t& nextx, uint32\_t& nexty)
 {
 uint32\_t addx = param->src\_x32\_add;
 uint32\_t addy = param->src\_y32\_add;
 uint\_fast8\_t r = \_internal\_rotation;
 uint\_fast8\_t bitr = 1u << r;
 // if (bitr & 0b10011100)
 // {
 // nextx = -nextx;
 // }
 if (bitr & 0b10010110) // case 1:2:4:7:
 {
 param->src\_y32 += nexty \* (h - 1);
 nexty = -(int32\_t)nexty;
 y = \_height - (y + h);
 }
 if (r & 2)
 {
 param->src\_x32 += addx \* (w - 1);
 param->src\_y32 += addy \* (w - 1);
 addx = -(int32\_t)addx;
 addy = -(int32\_t)addy;
 x = \_width - (x + w);
 }
 if (r & 1)
 {
 std::swap(x, y);
 std::swap(w, h);
 std::swap(nextx, addx);
 std::swap(nexty, addy);
 }
 param->src\_x32\_add = addx;
 param->src\_y32\_add = addy;
 }

 void Panel\_FrameBufferBase::writePixels(pixelcopy\_t\* param, uint32\_t length, bool use\_dma)
 {
 (void)use\_dma;
 uint\_fast16\_t xs = \_xs;
 uint\_fast16\_t xe = \_xe;
 uint\_fast16\_t ys = \_ys;
 uint\_fast16\_t ye = \_ye;
 uint\_fast16\_t x = \_xpos;
 uint\_fast16\_t y = \_ypos;
 const size\_t bytes = \_write\_bits >> 3;
 // auto k = \_bitwidth \* bits >> 3;

 uint\_fast8\_t r = \_internal\_rotation;
 int\_fast16\_t ax = 1;
 int\_fast16\_t ay = 1;
 if (r) {
 if ((1u << r) & 0b10010110) { y = \_height - (y + 1); ys = \_height - (ys + 1); ye = \_height - (ye + 1); ay = -1; }
 if (r & 2) { x = \_width - (x + 1); xs = \_width - (xs + 1); xe = \_width - (xe + 1); ax = -1; }
 }
 \_range\_mod.left = std::min(\_range\_mod.left , xs);
 \_range\_mod.right = std::max(\_range\_mod.right , xe);
 \_range\_mod.top = std::min(\_range\_mod.top , ys);
 \_range\_mod.bottom = std::max(\_range\_mod.bottom, ye);

 if (!r)
 {
 uint\_fast16\_t linelength;
 do {
 linelength = std::min(xe - x + 1, length);
 auto ptr = &\_lines\_buffer\[y\]\[x \* bytes\];
 param->fp\_copy(ptr, 0, linelength, param);
 // cacheWriteBack(ptr, bytes \* linelength);

 if ((x += linelength) > xe)
 {
 x = xs;
 y = (y != ye) ? (y + 1) : ys;
 }
 } while (length -= linelength);
 \_xpos = x;
 \_ypos = y;
 return;
 }

 if (r & 1)
 {
 do
 {
 param->fp\_copy(\_lines\_buffer\[x\], y, y + 1, param); /// xとyを入れ替えて処理する;
 if (x != xe)
 {
 x += ax;
 }
 else
 {
 x = xs;
 y = (y != ye) ? (y + ay) : ys;
 }
 } while (--length);
 }
 else
 {
 // int w = abs((int)(xe - xs)) + 1;
 do
 {
 param->fp\_copy(\_lines\_buffer\[y\], x, x + 1, param);
 if (x != xe)
 {
 x += ax;
 }
 else
 {
 x = xs;
 // cacheWriteBack(&\_lines\_buffer\[y\]\[x\], bytes \* w);
 y = (y != ye) ? (y + ay) : ys;
 }
 } while (--length);
 }

 if ((1u << r) & 0b10010110) { y = \_height - (y + 1); }
 if (r & 2) { x = \_width - (x + 1); }
 \_xpos = x;
 \_ypos = y;
 }

 void Panel\_FrameBufferBase::writeImage(uint\_fast16\_t x, uint\_fast16\_t y, uint\_fast16\_t w, uint\_fast16\_t h, pixelcopy\_t\* param, bool)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 uint32\_t nextx = 0;
 uint32\_t nexty = 1 << pixelcopy\_t::FP\_SCALE;
 if (r)
 {
 \_rotate\_pixelcopy(x, y, w, h, param, nextx, nexty);
 }
 \_range\_mod.left = std::min(x, \_range\_mod.left);
 \_range\_mod.right = std::max(x+w-1, \_range\_mod.right);
 \_range\_mod.top = std::min(y, \_range\_mod.top);
 \_range\_mod.bottom = std::max(y+h-1, \_range\_mod.bottom);

 if (r == 0 && param->transp == pixelcopy\_t::NON\_TRANSP && param->no\_convert)
 {
 auto bits = \_write\_bits;
 x = x \* bits >> 3;
 w = w \* bits >> 3;
 auto sw = param->src\_bitwidth \* bits >> 3;
 auto src = &((uint8\_t\*)param->src\_data)\[param->src\_y \* sw + (param->src\_x \* bits >> 3)\];
 h += y;
 do
 {
 memcpy(&\_lines\_buffer\[y\]\[x\], src, w);
 // cacheWriteBack(&\_lines\_buffer\[y\]\[x\], w);
 src += sw;
 } while (++y != h);
 return;
 }

 uint32\_t sx32 = param->src\_x32;
 uint32\_t sy32 = param->src\_y32;
 // uint\_fast8\_t bytes = \_write\_bits >> 3;
 h += y;
 do
 {
 int32\_t pos = x;
 int32\_t end = pos + w;
 while (end != (pos = param->fp\_copy(\_lines\_buffer\[y\], pos, end, param))
 && end != (pos = param->fp\_skip( pos, end, param)));
 param->src\_x32 = (sx32 += nextx);
 param->src\_y32 = (sy32 += nexty);
 // auto ptr = &\_lines\_buffer\[y\]\[x \* bytes\];
 // cacheWriteBack(ptr, bytes \* end);
 } while (++y != h);
 }

 void Panel\_FrameBufferBase::writeImageARGB(uint\_fast16\_t x, uint\_fast16\_t y, uint\_fast16\_t w, uint\_fast16\_t h, pixelcopy\_t\* param)
 {
 uint32\_t nextx = 0;
 uint32\_t nexty = 1 << pixelcopy\_t::FP\_SCALE;
 if (\_internal\_rotation)
 {
 \_rotate\_pixelcopy(x, y, w, h, param, nextx, nexty);
 }
 uint32\_t sx32 = param->src\_x32;
 uint32\_t sy32 = param->src\_y32;

 uint32\_t pos = x;
 uint32\_t end = pos + w;
 h += y;
 // uint\_fast16\_t wbytes = (w \* \_write\_bits) >> 3;
 do
 {
 param->fp\_copy(\_lines\_buffer\[y\], pos, end, param);
 // cacheWriteBack(&\_lines\_buffer\[y\]\[pos\], wbytes);
 param->src\_x32 = (sx32 += nextx);
 param->src\_y32 = (sy32 += nexty);
 } while (++y < h);
 }

 void Panel\_FrameBufferBase::readRect(uint\_fast16\_t x, uint\_fast16\_t y, uint\_fast16\_t w, uint\_fast16\_t h, void\* dst, pixelcopy\_t\* param)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 if (r == 0 && param->no\_convert)
 {
 h += y;
 auto bytes = \_write\_bits >> 3;
 auto d = (uint8\_t\*)dst;
 w \*= bytes;
 do
 {
 memcpy(d, &\_lines\_buffer\[y\]\[x \* bytes\], w);
 d += w;
 } while (++y != h);
 return;
 }

 int addx = 1;
 int addy = 1;
 uint\_fast16\_t wlen = 1;
 if (r)
 {
 if (r & 2)
 {
 x = \_width - (x + 1);
 param->src\_x32\_add = -param->src\_x32\_add;
 addx = -1;
 }
 if ((1 << r) & 0b10010110)
 {
 y = \_height - (y + 1);
 addy = -1;
 }
 if (r & 1)
 {
 std::swap(x, y);
 std::swap(w, h);
 std::swap(addx, addy);
 std::swap(wlen, w);
 std::swap(param->src\_x32\_add, param->src\_y32\_add);
 }
 }

 h = y + (h \* addy);
 uint\_fast32\_t pos = 0;
 uint\_fast16\_t ybak = y;
 do
 {
 y = ybak;
 uint32\_t x32 = x << pixelcopy\_t::FP\_SCALE;
 do
 {
 param->src\_y32 = 0;
 param->src\_x32 = x32;
 param->src\_data = \_lines\_buffer\[y\];
 param->fp\_copy(dst, pos, pos + w, param);
 pos += w;
 } while (h != (y += addy));
 x += addx;
 } while (--wlen);
 }

 void Panel\_FrameBufferBase::copyRect(uint\_fast16\_t dst\_x, uint\_fast16\_t dst\_y, uint\_fast16\_t w, uint\_fast16\_t h, uint\_fast16\_t src\_x, uint\_fast16\_t src\_y)
 {
 uint\_fast8\_t r = \_internal\_rotation;
 if (r)
 {
 if ((1u << r) & 0b10010110) { src\_y = \_height - (src\_y + h); dst\_y = \_height - (dst\_y + h); }
 if (r & 2) { src\_x = \_width - (src\_x + w); dst\_x = \_width - (dst\_x + w); }
 if (r & 1) { std::swap(src\_x, src\_y); std::swap(dst\_x, dst\_y); std::swap(w, h); }
 }
 \_range\_mod.left = std::min(\_range\_mod.left , dst\_x);
 \_range\_mod.right = std::max(\_range\_mod.right , dst\_x + w - 1);
 \_range\_mod.top = std::min(\_range\_mod.top , dst\_y);
 \_range\_mod.bottom = std::max(\_range\_mod.bottom, dst\_y + h - 1);

 size\_t bytes = \_write\_bits >> 3;
 size\_t len = w \* bytes;
 int32\_t add = 1;
 if (src\_y < dst\_y) add = -add;
 int32\_t pos = (src\_y < dst\_y) ? h - 1 : 0;

 /// PSRAMを使用している場合、PSRAM to PSRAMのmemcpyがデータ破損を起こす場合があるため、一旦ローカルの配列を経由してコピーを行う;
 auto buf = (uint8\_t\*)alloca(len);
 do
 {
 uint8\_t\* src = &\_lines\_buffer\[src\_y + pos\]\[src\_x \* bytes\];
 uint8\_t\* dst = &\_lines\_buffer\[dst\_y + pos\]\[dst\_x \* bytes\];
 memcpy(buf, src, len);
 memcpy(dst, buf, len);
 pos += add;
 } while (--h);
 }

//----------------------------------------------------------------------------
 }
}