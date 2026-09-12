; Private wider descriptor for the arena list; stock window 3 stays unchanged.
.gba
.thumb
.create "arena-list.bin", CODE_ADDRESS
ArenaList:
    push {r4-r7,lr}
    sub sp,0x90
    mov r1,1
    mov r2,1
    ldr r0,=DESCRIPTOR_ADDRESS
    ldr r3,=0x0806C815
    bl @@call
    ldr r3,=0x08079877
    bx r3
@@call:
    bx r3
.pool
.close
