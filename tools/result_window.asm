; Private result-detail window. Original list/history descriptors remain intact.
.gba
.thumb
.create "result-window.bin", CODE_ADDRESS
ResultWindow:
    push {lr}
    mov r1,0
    mov r2,1
    ldr r0,=DESCRIPTOR_ADDRESS
    ldr r3,=0x0806C815
    bl @@call
    pop {r3}
    mov lr,r3
    ldr r3,=RESUME_ADDRESS
    bx r3
@@call:
    bx r3
.pool
.close
