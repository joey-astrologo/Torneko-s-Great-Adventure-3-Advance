; Add English inscription matching, retaining the original Japanese fallback.
.gba
.thumb
.create "inscription-matcher.bin", CODE_ADDRESS
EnglishInscription:
    push {r0-r4,r6,lr}
    ldr r4,=ALIAS_TABLE
NextAlias:
    ldr r2,[r4]
    cmp r2,0
    beq Legacy
    add r3,sp,28 ; native decoded string before register-save frame
    mov r6,0
Compare:
    ldrb r0,[r3,r6]
    ldrb r1,[r2,r6]
    cmp r0,0x41
    blo FoldAlias
    cmp r0,0x5A
    bhi FoldAlias
    add r0,0x20
FoldAlias:
    cmp r1,0x41
    blo Compared
    cmp r1,0x5A
    bhi Compared
    add r1,0x20
Compared:
    cmp r0,r1
    bne Advance
    cmp r0,0
    beq Learned
    add r6,1
    cmp r6,8
    blo Compare
Advance:
    add r4,12
    b NextAlias
Learned:
    ldr r0,[r4,8]
    bl IsLearned
    cmp r0,0
    beq Legacy
    mov r7,r4
    pop {r0-r4,r6}
    pop {r0}
    mov lr,r0
    ldr r0,=0x0807F217
    bx r0
Legacy:
    pop {r0-r4,r6}
    pop {r0}
    mov lr,r0
    ldr r7,=0x0807F22C
    ldr r7,[r7]
    ldr r0,[r7]
    cmp r0,0
    beq Empty
    ldr r1,=0x0807F179
    bx r1
Empty:
    ldr r1,=0x0807F241
    bx r1
.align 4
IsLearned:
    ldr r1,=0x0800111D
    bx r1
.pool
.close
