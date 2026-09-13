; Native arrival constructor extensions. Entries +0 (upload), +4 (map).
; Reuse the native tile buffer and BG0 map; no permanent RAM allocation.
.gba
.thumb
.create "arrival-credits.bin", CODE_ADDRESS
    b Upload
    nop
    b Map
    nop

Upload:
    push {r4-r7,lr}
    bl SelectFloor
    mov r4,r0
    ldr r1,=0x020371DC
    mov r2,0xA0
    lsl r2,r2,3
    mov r0,0
@@clear:
    str r0,[r1]
    add r1,4
    sub r2,1
    bne @@clear
    ldr r0,[r4]
    ldr r2,[r4,8]
    ldr r1,=0x020371DC
@@copy:
    ldr r3,[r0]
    str r3,[r1]
    add r0,4
    add r1,4
    sub r2,1
    bne @@copy
    pop {r4-r7}
    pop {r0}
    mov lr,r0
    ldr r1,=0x02035DDC
    ldr r0,=0x08005229
    bx r0

Map:
    push {r4-r7,lr}
    ldr r0,=0x02004FF0
    ldrb r0,[r0]
    cmp r0,26
    beq @@done
    bl SelectFloor
    ldr r0,[r0,4]
    ldr r1,=0x020350DC ; BG0 row 12, column 0
    mov r2,4
@@row:
    mov r3,30
@@column:
    ldrh r4,[r0]
    strh r4,[r1]
    add r0,2
    add r1,2
    sub r3,1
    bne @@column
    add r1,4
    sub r2,1
    bne @@row
@@done:
    pop {r4-r7}
    pop {r0}
    mov lr,r0
    ldr r0,=0x08005395
    bx r0

SelectFloor:
    push {lr}
    ldr r3,=0x08004B6D
    bl @@call
    mov r2,0
    cmp r0,0
    beq @@ordinary
    mov r2,1
    lsl r2,r2,8
@@ordinary:
    ldr r0,=0x02004FF1
    ldrb r0,[r0]
    add r0,r0,r2
    lsl r1,r0,1
    add r0,r0,r1
    lsl r0,r0,2
    ldr r1,=FLOOR_RECORDS
    add r0,r0,r1
    pop {r1}
    bx r1
@@call:
    bx r3
    .pool
.close
