; Handle ASCII defaults only at the recruitment encoder call.
; Original Japanese and every other caller retain the original encoder.
.gba
.thumb
.create "nickname-code.bin", CODE_ADDRESS

EncodeRecruitNickname:
    push {r0,r3}
    mov r3,lr
    ldr r0,=0x080292BF
    cmp r3,r0
    bne @@original
    ldrb r0,[r2]
    cmp r0,0x80
    bhs @@original
    pop {r0,r3}
    push {r4-r7,lr}
    mov r4,r1
    mov r5,r2
    mov r6,0
    ldr r7,=ASCII_IDS
@@next:
    ldrb r0,[r5]
    cmp r0,0
    beq @@end
    add r5,1
    cmp r0,0x80
    blo @@ascii
    ; The native duplicate suffix is a single full-width digit.
    cmp r0,0x82
    bne @@end
    ldrb r0,[r5]
    add r5,1
    cmp r0,0x4F
    blo @@end
    cmp r0,0x58
    bhi @@end
    sub r0,0x1F
@@ascii:
    ldrb r0,[r7,r0]
    cmp r0,0
    beq @@end
    cmp r6,5
    blo @@append
    ; Full five-letter base plus suffix: keep first four and suffix.
    sub r4,1
    sub r6,1
@@append:
    strb r0,[r4]
    add r4,1
    add r6,1
    b @@next
@@end:
    mov r0,0
    strb r0,[r4]
    pop {r4-r7}
    pop {r0}
    bx r0
@@original:
    ; Restore type and execute the displaced original prologue.
    pop {r0,r3}
    b OriginalEncoder
    .pool

OriginalEncoder:
    push {r4-r7,lr}
    mov r7,r8
    push {r7}
    mov r3,r0
    ldr r0,=0x0807D2A5
    bx r0
    .pool
.close
