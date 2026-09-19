; Approved sentence spans only. Existing damage/XP wrapper remains the fallback.
.gba
.thumb
.create "combat-lines.bin", CODE_ADDRESS
FormatHook:
    mov r3,r12
    push {r4-r7,lr}
    sub sp,108
    mov r4,r0
    mov r5,r1
    mov r6,r2
    str r3,[sp,4]
    bl PreviousEntry
    str r0,[sp]
    ; Binary search of 16-byte records by exact source address.
    mov r0,0
    ldr r1,=RECORD_COUNT
@@search:
    cmp r0,r1
    blo @@search_more
    b @@done
@@search_more:
    mov r2,r0
    add r2,r2,r1
    lsr r2,r2,1
    lsl r7,r2,4
    ldr r3,=RECORD_TABLE
    add r7,r7,r3
    ldr r3,[r7]
    cmp r4,r3
    beq @@found
    blo @@lower
    mov r0,r2
    add r0,1
    b @@search
@@lower:
    mov r1,r2
    b @@search
@@found:
    str r7,[sp,8]
    ldr r0,[sp,4]
    cmp r0,0
    bne @@line
    ; Reject a destination filled to its terminator limit: it may be truncated.
    mov r0,r5
@@complete:
    cmp r0,r6
    blo @@read_complete
    b @@done
@@read_complete:
    ldrb r1,[r0]
    cmp r1,0
    beq @@full
    add r0,1
    b @@complete
@@full:
    mov r0,r5
    mov r1,r6
    mov r2,r7
    bl JoinSpan
    b @@done
@@line:
    ; Only the first source line of the approved span may consume lookahead.
    ldr r0,[r7,8]
    cmp r0,0
    bne @@done
    mov r0,r4
    add r1,sp,24
    mov r2,r1
    add r2,79
    mov r3,0
    bl PreviousEntry
    add r0,sp,24
    mov r1,r0
    add r1,79
    mov r2,r7
    bl JoinSpan
    cmp r0,0
    beq @@done
    ; r1 points at the span's terminating LF/NUL in scratch.
    add r2,sp,24
    mov r3,r1
    sub r3,r2
    mov r0,r6
    sub r0,r5
    cmp r3,r0
    bhi @@done
    mov r0,0
    strb r0,[r1]
    mov r0,r5
@@copy:
    ldrb r3,[r2]
    strb r3,[r0]
    add r0,1
    add r2,1
    cmp r3,0
    bne @@copy
    ldr r0,[r7,4]
    str r0,[sp]
@@done:
    ldr r0,[sp]
    add sp,108
    pop {r4-r7}
    pop {r1}
    bx r1
    .pool
PreviousEntry:
    ; Previous wrapper expects the same r12 line-mode convention as the ROM hook.
    mov r12,r3
    ldr r3,=PREVIOUS_CODE
    bx r3
    .pool

JoinSpan:
    ; r0 buffer, r1 inclusive terminator limit, r2 record.
    ; Return r0 success, r1 span end. Never modify a rejected span.
    push {r4-r7,lr}
    sub sp,12
    mov r4,r0
    mov r5,r1
    ldr r6,[r2,8]
    ldr r7,[r2,12]
    str r7,[sp,8]
@@skip:
    cmp r6,0
    beq @@marker
    cmp r4,r5
    bhs @@fail
    ldrb r0,[r4]
    cmp r0,0
    beq @@fail
    cmp r0,10
    bne @@skip_next
    sub r6,1
@@skip_next:
    add r4,1
    b @@skip
@@marker:
    ; High flag: source has a leading history continuation marker.
    lsr r0,r7,8
    cmp r0,0
    beq @@start
    ldrb r0,[r4]
    cmp r0,33
    bne @@start
    add r4,1
@@start:
    mov r0,255
    and r7,r0
    str r4,[sp]
    mov r6,0
    str r6,[sp,4]
@@scan:
    cmp r4,r5
    bhs @@fail
    ldrb r0,[r4]
    cmp r0,0
    beq @@end
    cmp r0,10
    bne @@glyph
    cmp r7,0
    beq @@end
    sub r7,1
    mov r0,32
@@glyph:
    cmp r0,32
    blo @@fail
    cmp r0,126
    bhi @@fail
    ldr r1,=WIDTH_TABLE
    ldrb r0,[r1,r0]
    add r6,r6,r0
    cmp r6,208
    bhi @@fail
    ldr r0,[sp,4]
    add r0,1
    cmp r0,59
    bhi @@fail
    str r0,[sp,4]
    add r4,1
    b @@scan
@@end:
    cmp r7,0
    bne @@fail
    mov r1,r4
    ldr r2,[sp]
@@replace:
    cmp r2,r4
    beq @@success
    ldrb r0,[r2]
    cmp r0,10
    bne @@next
    mov r0,32
    strb r0,[r2]
@@next:
    add r2,1
    b @@replace
@@success:
    mov r0,1
    b @@return
@@fail:
    mov r0,0
@@return:
    add sp,12
    pop {r4-r7}
    pop {r2}
    bx r2
    .pool
.close
