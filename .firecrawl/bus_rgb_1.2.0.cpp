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
#if defined (ESP\_PLATFORM)
#include
#if defined (CONFIG\_IDF\_TARGET\_ESP32S3)
#if \_\_has\_include ()
#include "Bus\_RGB.hpp"

#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include
#include

#if \_\_has\_include ()
 #include
#else
 #include
#endif

namespace lgfx
{
 inline namespace v1
 {
//----------------------------------------------------------------------------

 static \_\_attribute\_\_ ((always\_inline)) inline volatile uint32\_t\* reg(uint32\_t addr) { return (volatile uint32\_t \*)ETS\_UNCACHED\_ADDR(addr); }

 static lcd\_cam\_dev\_t\* getDev(int port)
 {
 return &LCD\_CAM;
 }

 void Bus\_RGB::config(const config\_t& cfg)
 {
 \_cfg = cfg;
 }

 IRAM\_ATTR void Bus\_RGB::lcd\_default\_isr\_handler(void \*args)
 {
 Bus\_RGB \*me = (Bus\_RGB\*)args;
 auto dev = getDev(me->config().port);

 uint32\_t intr\_status = dev->lc\_dma\_int\_st.val & 0x03;
 dev->lc\_dma\_int\_clr.val = intr\_status;
 if (intr\_status & LCD\_LL\_EVENT\_VSYNC\_END) {
 GDMA.channel\[me->\_dma\_ch\].out.conf0.out\_rst = 1;
 GDMA.channel\[me->\_dma\_ch\].out.conf0.out\_rst = 0;
 GDMA.channel\[me->\_dma\_ch\].out.link.addr = (uintptr\_t)&(me->\_dmadesc\_restart);
 GDMA.channel\[me->\_dma\_ch\].out.link.start = 1;

 // bool need\_yield = false;
 // call user registered callback
 // if (rgb\_panel->on\_vsync) {
 // if (rgb\_panel->on\_vsync(&rgb\_panel->base, NULL, rgb\_panel->user\_ctx)) {
 // need\_yield = true;
 // }
 // }

 // check whether to update the PCLK frequency, it should be safe to update the PCLK frequency in the VSYNC interrupt
 // lcd\_rgb\_panel\_try\_update\_pclk(rgb\_panel);

 // if (need\_yield) {
 // portYIELD\_FROM\_ISR();
 // }
 }
 }

 static void \_gpio\_pin\_sig(uint32\_t pin, uint32\_t sig)
 {
 gpio\_hal\_iomux\_func\_sel(GPIO\_PIN\_MUX\_REG\[pin\], PIN\_FUNC\_GPIO);
 gpio\_set\_direction((gpio\_num\_t)pin, GPIO\_MODE\_OUTPUT);
 esp\_rom\_gpio\_connect\_out\_signal(pin, sig, false, false);
 }

 bool Bus\_RGB::init(void)
 {
// ここでは ESP-IDFのLCDドライバに初期化部分だけ任せる
// 本来なら esp\_lcd\_rgb\_panel\_config\_t を使ってRGBバスを作成するところだが、
// フレームバッファの確保やイベントハンドラは自前で処理したいので、敢えて i80バスを作成する。
/\*
 esp\_lcd\_rgb\_panel\_config\_t \_panel\_config;

 memset(&\_panel\_config, 0, sizeof(\_panel\_config));
 \_panel\_config.clk\_src = LCD\_CLK\_SRC\_PLL160M;
 \_panel\_config.timings.pclk\_hz = \_cfg.freq\_write;
 \_panel\_config.timings.h\_res = 1;//\_cfg.panel->width();
 \_panel\_config.timings.v\_res = 1;//\_cfg.panel->height();

 \_panel\_config.data\_width = 16;
 // \_panel\_config->data\_width = \_cfg.panel->getWriteDepth() & color\_depth\_t::bit\_mask; // RGB565 in parallel mode, thus 16bit in width

 \_panel\_config.sram\_trans\_align = 8;
 \_panel\_config.psram\_trans\_align = 64;
 \_panel\_config.hsync\_gpio\_num = \_cfg.pin\_hsync;
 \_panel\_config.vsync\_gpio\_num = \_cfg.pin\_vsync;
 \_panel\_config.de\_gpio\_num = \_cfg.pin\_henable;
 \_panel\_config.pclk\_gpio\_num = \_cfg.pin\_pclk;
 \_panel\_config.disp\_gpio\_num = GPIO\_NUM\_NC;

 for (int i = 0; i < 16; ++ i) {
 \_panel\_config.data\_gpio\_nums\[i\] = \_cfg.pin\_data\[i\];
 }
 \_panel\_config.flags.fb\_in\_psram = 1; // allocate frame buffer in PSRAM

 ESP\_ERROR\_CHECK(esp\_lcd\_new\_rgb\_panel(&\_panel\_config, &\_panel\_handle));
/\*/
 // dummy settings.
 esp\_lcd\_i80\_bus\_config\_t bus\_config;
 memset(&bus\_config, 0, sizeof(esp\_lcd\_i80\_bus\_config\_t));
 // bus\_config.dc\_gpio\_num = GPIO\_NUM\_NC;
 bus\_config.dc\_gpio\_num = \_cfg.pin\_vsync;
 bus\_config.wr\_gpio\_num = \_cfg.pin\_pclk;
 bus\_config.clk\_src = lcd\_clock\_source\_t::LCD\_CLK\_SRC\_PLL160M;
 for (int i = 0; i < 16; ++i)
 {
 bus\_config.data\_gpio\_nums\[i^8\] = \_cfg.pin\_data\[i\];
 }
 bus\_config.bus\_width = 16;
 bus\_config.max\_transfer\_bytes = 4092;

 if (ESP\_OK != esp\_lcd\_new\_i80\_bus(&bus\_config, &\_i80\_bus)) {
 return false;
 }
 uint8\_t pixel\_bytes = (\_cfg.panel->getWriteDepth() & bit\_mask) >> 3;
 auto dev = getDev(\_cfg.port);

 {
 static constexpr const uint8\_t rgb332sig\_tbl\[\] = { 1, 0, 1, 0, 1, 2, 3, 4, 2, 3, 4, 5, 6, 5, 6, 7 };
 static constexpr const uint8\_t rgb565sig\_tbl\[\] = { 8, 9, 10, 11, 12, 13, 14, 15, 0, 1, 2, 3, 4, 5, 6, 7 };
 auto tbl = (pixel\_bytes == 2) ? rgb565sig\_tbl : rgb332sig\_tbl;
#if SOC\_LCDCAM\_RGB\_LCD\_SUPPORTED
 auto sigs = &lcd\_periph\_rgb\_signals.panels\[\_cfg.port\];
#else
 auto sigs = &lcd\_periph\_signals.panels\[\_cfg.port\];
#endif
 for (size\_t i = 0; i < 16; i++) {
 \_gpio\_pin\_sig(\_cfg.pin\_data\[i\], sigs->data\_sigs\[tbl\[i\]\]);
 }
 \_gpio\_pin\_sig(\_cfg.pin\_henable, sigs->de\_sig);
 \_gpio\_pin\_sig(\_cfg.pin\_hsync, sigs->hsync\_sig);
 \_gpio\_pin\_sig(\_cfg.pin\_vsync, sigs->vsync\_sig);
 \_gpio\_pin\_sig(\_cfg.pin\_pclk, sigs->pclk\_sig);
 }

 // periph\_module\_enable(lcd\_periph\_signals.panels\[\_cfg.port\].module);
 \_dma\_ch = search\_dma\_out\_ch(SOC\_GDMA\_TRIG\_PERIPH\_LCD0);
 if (\_dma\_ch < 0)
 {
 esp\_lcd\_del\_i80\_bus(\_i80\_bus);
 ESP\_LOGE("Bus\_RGB", "DMA channel not found...");
 return false;
 }

 GDMA.channel\[\_dma\_ch\].out.peri\_sel.sel = SOC\_GDMA\_TRIG\_PERIPH\_LCD0;

 typeof(GDMA.channel\[0\].out.conf0) conf0;
 conf0.val = 0;
 conf0.out\_eof\_mode = 1;
 conf0.outdscr\_burst\_en = 1;
 conf0.out\_data\_burst\_en = 1;
 GDMA.channel\[\_dma\_ch\].out.conf0.val = conf0.val;

 typeof(GDMA.channel\[0\].out.conf1) conf1;
 conf1.val = 0;
 conf1.out\_ext\_mem\_bk\_size = GDMA\_LL\_EXT\_MEM\_BK\_SIZE\_64B;
 GDMA.channel\[\_dma\_ch\].out.conf1.val = conf1.val;

 size\_t fb\_len = (\_cfg.panel->width() \* pixel\_bytes) \* \_cfg.panel->height();
 auto data = (uint8\_t\*)heap\_alloc\_psram(fb\_len);
 \_frame\_buffer = data;
 static constexpr size\_t MAX\_DMA\_LEN = (4096-64);
 size\_t dmadesc\_size = (fb\_len - 1) / MAX\_DMA\_LEN + 1;
 auto dmadesc = (dma\_descriptor\_t\*)heap\_caps\_malloc(sizeof(dma\_descriptor\_t) \* dmadesc\_size, MALLOC\_CAP\_DMA);
 \_dmadesc = dmadesc;

 size\_t len = fb\_len;
 while (len > MAX\_DMA\_LEN)
 {
 len -= MAX\_DMA\_LEN;
 dmadesc->buffer = (uint8\_t \*)data;
 data += MAX\_DMA\_LEN;
 \*(uint32\_t\*)dmadesc = MAX\_DMA\_LEN \| MAX\_DMA\_LEN << 12 \| 0x80000000;
 dmadesc->next = dmadesc + 1;
 dmadesc++;
 }
 \*(uint32\_t\*)dmadesc = ((len + 3) & ( ~3 )) \| len << 12 \| 0xC0000000;
 dmadesc->buffer = (uint8\_t \*)data;
 dmadesc->next = \_dmadesc;
 GDMA.channel\[\_dma\_ch\].out.link.addr = (uintptr\_t)&(\_dmadesc);
 GDMA.channel\[\_dma\_ch\].out.link.start = 1;
 //////////////////////////////////////////////

 memcpy(&\_dmadesc\_restart, \_dmadesc, sizeof(\_dmadesc\_restart));
 int skip\_bytes = (GDMA\_LL\_L2FIFO\_BASE\_SIZE + 1) \* pixel\_bytes;
 auto p = (uint8\_t\*)(\_dmadesc\_restart.buffer);
 \_dmadesc\_restart.buffer = &p\[skip\_bytes\];
 \_dmadesc\_restart.dw0.length -= skip\_bytes;
 \_dmadesc\_restart.dw0.size -= skip\_bytes;

 uint32\_t hsw = \_cfg.hsync\_pulse\_width;
 uint32\_t hbp = \_cfg.hsync\_back\_porch;
 uint32\_t active\_width = \_cfg.panel->width();
 uint32\_t hfp = \_cfg.hsync\_front\_porch;

 uint32\_t vsw = \_cfg.vsync\_pulse\_width;
 uint32\_t vbp = \_cfg.vsync\_back\_porch;
 uint32\_t vfp = \_cfg.vsync\_front\_porch;
 uint32\_t active\_height = \_cfg.panel->height();

 uint32\_t div\_a, div\_b, div\_n, clkcnt;
 calcClockDiv(&div\_a, &div\_b, &div\_n, &clkcnt, 240\*1000\*1000, std::min(\_cfg.freq\_write, 40000000u));
 typeof(dev->lcd\_clock) lcd\_clock;
 lcd\_clock.lcd\_clkcnt\_n = std::max(1u, clkcnt - 1);
 lcd\_clock.lcd\_clk\_equ\_sysclk = (clkcnt == 1);
 lcd\_clock.lcd\_ck\_idle\_edge = false;
 lcd\_clock.lcd\_ck\_out\_edge = \_cfg.pclk\_idle\_high;
 lcd\_clock.lcd\_clkm\_div\_num = div\_n;
 lcd\_clock.lcd\_clkm\_div\_b = div\_b;
 lcd\_clock.lcd\_clkm\_div\_a = div\_a;
 lcd\_clock.lcd\_clk\_sel = 2; // clock\_select: 1=XTAL CLOCK / 2=240MHz / 3=160MHz
 lcd\_clock.clk\_en = true;
 dev->lcd\_clock.val = lcd\_clock.val;

 typeof(dev->lcd\_user) lcd\_user;
 lcd\_user.val = 0;
 // lcd\_user.lcd\_dout\_cyclelen = 0;
 lcd\_user.lcd\_always\_out\_en = true;
 // lcd\_user.lcd\_8bits\_order = false;
 // lcd\_user.lcd\_update = false;
 // lcd\_user.lcd\_bit\_order = false;
 // lcd\_user.lcd\_byte\_order = false;
 lcd\_user.lcd\_2byte\_en = pixel\_bytes > 1; // RGB565 or RGB332
 lcd\_user.lcd\_dout = 1;
 // lcd\_user.lcd\_dummy = 0;
 // lcd\_user.lcd\_cmd = 0;
 lcd\_user.lcd\_update = 1;
 lcd\_user.lcd\_reset = 1; // self clear
 // lcd\_user.lcd\_reset = 0;
 lcd\_user.lcd\_dummy\_cyclelen = 3;
 // lcd\_user.lcd\_cmd\_2\_cycle\_en = 0;
 dev->lcd\_user.val = lcd\_user.val;

 typeof(dev->lcd\_misc) lcd\_misc;
 lcd\_misc.val = 0;
 lcd\_misc.lcd\_afifo\_reset = true;
 lcd\_misc.lcd\_next\_frame\_en = true;
 lcd\_misc.lcd\_bk\_en = true;
 // lcd\_misc.lcd\_vfk\_cyclelen = 0;
 // lcd\_misc.lcd\_vbk\_cyclelen = 0;
 dev->lcd\_misc.val = lcd\_misc.val;

 typeof(dev->lcd\_ctrl) lcd\_ctrl;
 lcd\_ctrl.lcd\_hb\_front = hbp + hsw - 1;
 lcd\_ctrl.lcd\_va\_height = active\_height - 1;
 lcd\_ctrl.lcd\_vt\_height = vsw + vbp + active\_height + vfp - 1;
 lcd\_ctrl.lcd\_rgb\_mode\_en = true;
 dev->lcd\_ctrl.val = lcd\_ctrl.val;

 typeof(dev->lcd\_ctrl1) lcd\_ctrl1;
 lcd\_ctrl1.lcd\_vb\_front = vbp + vsw - 1;
 lcd\_ctrl1.lcd\_ha\_width = active\_width - 1;
 lcd\_ctrl1.lcd\_ht\_width = hsw + hbp + active\_width + hfp - 1;
 dev->lcd\_ctrl1.val = lcd\_ctrl1.val;

 typeof(dev->lcd\_ctrl2) lcd\_ctrl2;
 lcd\_ctrl2.val = 0;
 lcd\_ctrl2.lcd\_vsync\_width = vsw - 1;
 lcd\_ctrl2.lcd\_vsync\_idle\_pol = \_cfg.vsync\_polarity;
 lcd\_ctrl2.lcd\_hs\_blank\_en = true;
 lcd\_ctrl2.lcd\_hsync\_width = hsw - 1;
 lcd\_ctrl2.lcd\_hsync\_idle\_pol = \_cfg.hsync\_polarity;
 // lcd\_ctrl2.lcd\_hsync\_position = 0;
 lcd\_ctrl2.lcd\_de\_idle\_pol = \_cfg.de\_idle\_high;
 dev->lcd\_ctrl2.val = lcd\_ctrl2.val;

 dev->lc\_dma\_int\_ena.val = 1;

 int isr\_flags = ESP\_INTR\_FLAG\_INTRDISABLED \| ESP\_INTR\_FLAG\_SHARED;

#if SOC\_LCDCAM\_RGB\_LCD\_SUPPORTED
 auto sigs = &lcd\_periph\_rgb\_signals.panels\[\_cfg.port\];
#else
 auto sigs = &lcd\_periph\_signals.panels\[\_cfg.port\];
#endif

 esp\_intr\_alloc\_intrstatus(sigs->irq\_id, isr\_flags,
 (uint32\_t)&dev->lc\_dma\_int\_st,
 LCD\_LL\_EVENT\_VSYNC\_END, lcd\_default\_isr\_handler, this, &\_intr\_handle);
 esp\_intr\_enable(\_intr\_handle);

 dev->lcd\_user.lcd\_update = 1;
 dev->lcd\_user.lcd\_start = 1;

 return true;
 }

 uint8\_t\* Bus\_RGB::getDMABuffer(uint32\_t length)
 {
 return \_frame\_buffer;
 // return \_rgb\_panel->fb;
 }

 void Bus\_RGB::release(void)
 {
 }

//----------------------------------------------------------------------------
 }
}

#endif
#endif
#endif