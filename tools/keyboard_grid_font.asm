; Keep English UI in font 0 and the unchanged kana password grid in font 1.
.gba
.thumb
.create "keyboard-grid-font.bin", CODE_ADDRESS

SelectGridFont:
    push {r3,lr}
    ldr r0,[sp,0x98] ; original keyboard-local codec type at sp+90
    mov r1,0
    bl SetFont
    pop {r3}
    pop {r0}
    mov lr,r0
    ; Replay 0807BE08..0807BE0F. r3 is overwritten at 0807BE10.
    ldr r2,=0x0807BEE8
    ldr r2,[r2]
    mov r1,r8
    ldr r0,[r1]
    lsl r0,r0,2
    ldr r3,=0x0807BE11
    bx r3

.align 4
RestoreFontZero:
    push {r3,lr}
    mov r0,0
    mov r1,0
    bl SetFont
    pop {r3}
    pop {r0}
    mov lr,r0
    ; r0 was 1 immediately before the hook. Replay 0807BE30..0807BE37.
    mov r0,1
    str r0,[sp]
    mov r1,0
    mov r2,0x62
    ldr r3,=0x0807BE39
    mov lr,r3
    mov r3,0xD0
    bx lr ; the resumed BL immediately supplies its own return address

.align 4
SetFont:
    ldr r2,=0x0808CD71
    bx r2
.pool
.close
