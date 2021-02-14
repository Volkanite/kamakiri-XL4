#include "common.h"

void (*jump_bl)(void) = (void*) 0xB673;
void (*send_usb_response)(int, int, int) = (void*)0x2D2B;
void (**ptr_send)() = (void*)0x103088;
void (**ptr_recv)() = (void*)0x103084;
void (*orig_ptr_send)();
void (*orig_ptr_recv)();

void (*send_dword)(uint32_t, int) = (void*)0xBCD3;
uint32_t (*recv_dword)() = (void*)0xBC9F;
// addr, sz
int (*send_data)() = (void*)0xBED1;
// addr, sz, flags (=0)
void (*recv_data)(int, uint32_t, uint32_t) = (void*)0xBD15;

void low_uart_put(int ch) {
    volatile uint32_t *uart_reg0 = (volatile uint32_t*)0x11003014;
    volatile uint32_t *uart_reg1 = (volatile uint32_t*)0x11003000;

    while ( !((*uart_reg0) & 0x20) )
    {}

    *uart_reg1 = ch;
}

void _putchar(char character)
{
    if (character == '\n')
        low_uart_put('\r');
    low_uart_put(character);
}
