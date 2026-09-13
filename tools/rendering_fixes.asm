; Only the four XP/level templates may join their final numeric line.
; Original formatting and return value are preserved for every caller.
.gba
.thumb
.create "rendering-fixes.bin", CODE_ADDRESS

FormatHook:
    mov r3,r12
    push {r4-r7,lr}
    sub sp,92
    mov r4,r0
    mov r5,r1
    mov r6,r2
    mov r7,r3
    bl OriginalEntry
    str r0,[sp]
    cmp r7,0
    bne @@line_mode
    ldr r0,=MESSAGE_0
    cmp r4,r0
    beq @@join
    ldr r0,=MESSAGE_1
    cmp r4,r0
    beq @@join
    ldr r0,=MESSAGE_2
    cmp r4,r0
    beq @@join
    ldr r0,=MESSAGE_3
    cmp r4,r0
    bne @@done
@@join:
    mov r0,r5
    mov r1,r6
    bl JoinNumberLine
    b @@done
@@line_mode:
    ; Queue/history asks the formatter for one source line at a time.
    ; Look ahead only from the verified prefix of the final numeric pair.
    ldr r0,=LINE_0
    cmp r4,r0
    beq @@lookahead
    ldr r0,=LINE_1
    cmp r4,r0
    beq @@lookahead
    ldr r0,=LINE_2
    cmp r4,r0
    beq @@lookahead
    ldr r0,=LINE_3
    cmp r4,r0
    bne @@done
@@lookahead:
    mov r0,r4
    add r1,sp,8
    mov r2,r1
    add r2,79
    mov r3,0
    bl OriginalEntry
    str r0,[sp,4]
    add r0,sp,8
    mov r1,r0
    add r1,79
    bl JoinNumberLine
    add r2,sp,8
    mov r1,0
@@length:
    ldrb r0,[r2,r1]
    cmp r0,10
    beq @@done
    cmp r0,13
    beq @@done
    cmp r0,0
    beq @@capacity
    add r1,1
    cmp r1,59
    bhi @@done
    b @@length
@@capacity:
    mov r0,r6
    sub r0,r5
    cmp r1,r0
    bhi @@done
    mov r0,r5
@@copy:
    ldrb r3,[r2]
    strb r3,[r0]
    add r0,1
    add r2,1
    cmp r3,0
    bne @@copy
    ldr r0,[sp,4]
    str r0,[sp]
@@done:
    ldr r0,[sp]
    add sp,92
    pop {r4-r7}
    pop {r1}
    bx r1
    .pool

OriginalEntry:
    ; Exact displaced prologue from 0807D8CC..0807D8D8.
    push {r4-r7,lr}
    mov r7,r8
    push {r7}
    sub sp,0x3C
    mov r4,r0
    mov r5,r1
    ldr r0,=0x0807D8D9
    bx r0
    .pool

JoinNumberLine:
    ; r0: formatted buffer, r1: original terminator limit.
    ; Replace one LF with space; never change the byte count or terminator.
    push {r4-r7,lr}
    sub sp,4
    mov r4,r0
    mov r5,r1
    mov r6,0
    mov r7,r0
@@scan:
    cmp r4,r5
    bhi @@return
    ldrb r0,[r4]
    cmp r0,0
    beq @@measure
    cmp r0,10
    bne @@advance
    mov r6,r4
    str r7,[sp]
    mov r7,r4
    add r7,1
@@advance:
    add r4,1
    b @@scan
@@measure:
    cmp r6,0
    beq @@return
    ; The selected templates end in their numeric XP/level line.
    ; Keep the original wrapping for any unexpected continuation/control.
    ldrb r0,[r7]
    cmp r0,45
    beq @@number
    cmp r0,48
    blo @@return
    cmp r0,57
    bhi @@return
@@number:
    ldr r7,[sp]
    mov r0,r4
    sub r0,r7
    cmp r0,59
    bhi @@return
    ldr r3,=WIDTH_TABLE
    mov r2,0
@@glyph:
    cmp r7,r4
    beq @@replace
    ldrb r0,[r7]
    cmp r7,r6
    bne @@ordinary
    mov r0,32
@@ordinary:
    cmp r0,32
    blo @@return
    cmp r0,126
    bhi @@return
    ldrb r1,[r3,r0]
    add r2,r2,r1
    cmp r2,208
    bhi @@return
    add r7,1
    b @@glyph
@@replace:
    mov r0,32
    strb r0,[r6]
@@return:
    add sp,4
    pop {r4-r7}
    pop {r0}
    bx r0
    .pool

TownLocation:
    push {r4-r6,lr}
    bl TownGetter
    ldr r4,=TOWN_NAMES
@@entry:
    ldr r1,[r4]
    cmp r1,0
    beq @@done
    cmp r0,r1
    beq @@found
    add r4,8
    b @@entry
@@found:
    ldr r0,[r4,4]
@@done:
    pop {r4-r6}
    pop {r1}
    mov r2,r0
    add r0,sp,4
    ldr r3,=0x0807625D
    bx r3
    .pool
TownGetter:
    ldr r3,=0x0806040D
    bx r3
    .pool
.close
