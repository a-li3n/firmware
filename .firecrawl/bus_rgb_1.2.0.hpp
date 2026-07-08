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
#pragma once

#if \_\_has\_include ()
#include
#include
#include
#include
#include

#include
#include

#include "../../Bus.hpp"
#include "../../panel/Panel\_FrameBufferBase.hpp"
#include "../common.hpp"

struct lcd\_cam\_dev\_t;
struct esp\_rgb\_panel\_t;

namespace lgfx
{
 inline namespace v1
 {
//----------------------------------------------------------------------------

 class Bus\_RGB : public IBus
 {
 public:
 struct config\_t
 {
 Panel\_FrameBufferBase\* panel = nullptr;

 // LCD\_CAM peripheral number. No need to change (only 0 for ESP32-S3.)
 int8\_t port = 0;

 // pixel clock
 uint32\_t freq\_write = 16000000;

 int8\_t pin\_pclk = -1;
 int8\_t pin\_vsync = -1;
 int8\_t pin\_hsync = -1;
 int8\_t pin\_henable = -1;
 union
 {
 int8\_t pin\_data\[16\];
 struct
 {
 int8\_t pin\_d0;
 int8\_t pin\_d1;
 int8\_t pin\_d2;
 int8\_t pin\_d3;
 int8\_t pin\_d4;
 int8\_t pin\_d5;
 int8\_t pin\_d6;
 int8\_t pin\_d7;
 int8\_t pin\_d8;
 int8\_t pin\_d9;
 int8\_t pin\_d10;
 int8\_t pin\_d11;
 int8\_t pin\_d12;
 int8\_t pin\_d13;
 int8\_t pin\_d14;
 int8\_t pin\_d15;
 };
 };

 int8\_t hsync\_pulse\_width = 0;
 int8\_t hsync\_back\_porch = 0;
 int8\_t hsync\_front\_porch = 0;
 int8\_t vsync\_pulse\_width = 0;
 int8\_t vsync\_back\_porch = 0;
 int8\_t vsync\_front\_porch = 0;
 bool hsync\_polarity = 0;
 bool vsync\_polarity = 0;
 bool pclk\_active\_neg = 1;
 bool de\_idle\_high = 0;
 bool pclk\_idle\_high = 0;
 };

 const config\_t& config(void) const { return \_cfg; }
 void config(const config\_t& config);

 bus\_type\_t busType(void) const override { return bus\_type\_t::bus\_unknown; }

 bool init(void) override;
 void release(void) override;

 void beginTransaction(void) override {}
 void endTransaction(void) override {}
 void wait(void) override {}
 bool busy(void) const override { return false; }

 void flush(void) override {}
 bool writeCommand(uint32\_t data, uint\_fast8\_t bit\_length) override { return true; }
 void writeData(uint32\_t data, uint\_fast8\_t bit\_length) override {}
 void writeDataRepeat(uint32\_t data, uint\_fast8\_t bit\_length, uint32\_t count) override {}
 void writePixels(pixelcopy\_t\* param, uint32\_t length) override {}
 void writeBytes(const uint8\_t\* data, uint32\_t length, bool dc, bool use\_dma) override {}

 void initDMA(void) override {}
 void addDMAQueue(const uint8\_t\* data, uint32\_t length) override {}
 void execDMAQueue(void) override {}
 uint8\_t\* getDMABuffer(uint32\_t length) override;

 void beginRead(void) override {}
 void endRead(void) override {}
 uint32\_t readData(uint\_fast8\_t bit\_length) override { return 0; }
 bool readBytes(uint8\_t\* dst, uint32\_t length, bool use\_dma) override { return false; }
 void readPixels(void\* dst, pixelcopy\_t\* param, uint32\_t length) override {}

 private:
 config\_t \_cfg;

 dma\_descriptor\_t \_dmadesc\_restart;
 dma\_descriptor\_t\* \_dmadesc = nullptr;
 esp\_lcd\_i80\_bus\_handle\_t \_i80\_bus = nullptr;
 int32\_t \_dma\_ch;

 esp\_lcd\_panel\_handle\_t \_panel\_handle = nullptr;

 uint8\_t \*\_frame\_buffer = nullptr;
 intr\_handle\_t \_intr\_handle;
 static void lcd\_default\_isr\_handler(void \*args);
 };

//----------------------------------------------------------------------------
 }
}
#endif