; ARM7TDMI code used by build_name_entry.py. All original Japanese glyph IDs
; remain valid. New Latin IDs map to single-byte font-0 codes.
.gba
.thumb
.create "name-code.bin", CODE_ADDRESS

ConvertName:
    push {r4-r6,lr}
    mov r6,r0
    mov r4,r1
    mov r5,r2
@@next:
    ldrb r1,[r5]
    cmp r1,0
    beq @@end
    mov r0,r6
    bl Lookup
    cmp r0,0xFF
    bls @@single
    lsr r1,r0,8
    strb r1,[r4]
    add r4,1
@@single:
    strb r0,[r4]
    add r4,1
    add r5,1
    b @@next
@@end:
    mov r0,0
    strb r0,[r4]
    pop {r4-r6}
    pop {r0}
    bx r0

.align 4
ConvertSlots:
    push {r4-r7,lr}
    mov r7,r0
    mov r4,r1
    mov r6,r2
    mov r5,r3
@@next:
    cmp r5,0
    beq @@end
    ldrb r1,[r6]
    mov r0,r7
    bl Lookup
    cmp r0,0xFF
    bls @@single
    lsr r1,r0,8
    strb r1,[r4]
    add r4,1
@@single:
    strb r0,[r4]
    add r4,1
    add r6,1
    sub r5,1
    b @@next
@@end:
    mov r0,0
    strb r0,[r4]
    pop {r4-r7}
    pop {r0}
    bx r0

.align 4
Lookup:
    ldr r2,=0x0807D20D
    bx r2
    .pool
.close
