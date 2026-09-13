; Move the already constructed title map, then place the existing floor map.
; Entry replaces the complete arrival-credits.map hook. Artwork stays intact.
.gba
.thumb
.create "arrival-layout.bin", CODE_ADDRESS
Layout:
    push {r4-r7,lr}
    ldr r0,=0x02004FF0
    ldrb r0,[r0]
    mov r5,4               ; ordinary title: +32 px
    cmp r0,26
    bne @@offset
    mov r5,6               ; arena title only: +48 px
@@offset:
    lsl r5,r5,6            ; 64 bytes per BG map row
    ldr r4,=0x0203501E     ; existing title row 9, column 1
    mov r7,9
@@title_row:
    mov r6,r4
    add r6,r6,r5
    mov r2,29
@@title_cell:
    ldrh r0,[r4]
    strh r0,[r6]
    mov r0,0
    strh r0,[r4]
    add r4,2
    add r6,2
    sub r2,1
    bne @@title_cell
    sub r4,122             ; move back one row after its 29 cells
    sub r7,1
    bne @@title_row
    ldr r0,=0x02004FF0
    ldrb r0,[r0]
    cmp r0,26
    beq @@done
    bl SelectFloor
    ldr r0,[r0,4]
    ldr r1,=0x0203505C     ; floor map row 10: -16 px
    mov r2,4
@@floor_row:
    mov r3,30
@@floor_cell:
    ldrh r4,[r0]
    strh r4,[r1]
    add r0,2
    add r1,2
    sub r3,1
    bne @@floor_cell
    add r1,4
    sub r2,1
    bne @@floor_row
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
