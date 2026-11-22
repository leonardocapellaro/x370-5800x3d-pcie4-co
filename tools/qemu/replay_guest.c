/* replay_guest.c — VM-only EFI application: replays a board capture.
   Loads A2.BIN (the archived capture from capture_format.h, 1168 SMN reads
   of one real boot at DXE entry) from the emulated FAT disk, validates it
   field by field, then runs the user's probe_check() (probe_api.h) against
   it. Every consult goes to the debug console (QEMU -debugcon 0xe9) as
   "SMN <addr> MEASURED <value>" or "SMN <addr> NOT_CAPTURED".
   Exit via isa-debug-exit 0xf4: 0=PASS, 1=FAIL, 2=INCONCLUSIVE, 4=bad input.
   Built by replay_run.py with clang/lld against EDK2 headers (docs/14). */
#include "probe_api.h"
#include "capture_format.h"

/* VM-only executable. Serial diagnostics are emitted on QEMU's debug console. */
static struct { UINT32 attrs; SMN_LOG log; UINT32 extra; } sample;
static BOOLEAN missing;
static UINTN queries;

static VOID print(const char *s) {
    while (*s) {
        __asm__ volatile("outb %0,$0xe9" :: "a"((UINT8)*s));
        ++s;
    }
}
static VOID hex32(UINT32 v) {
    char text[9];
    for (UINTN i = 0; i < 8; ++i) text[i] = "0123456789abcdef"[(v >> (28 - i*4)) & 15];
    text[8] = 0;
    print(text);
}
__attribute__((noreturn)) static VOID stop(UINT32 code) {
    __asm__ volatile("outl %0,$0xf4" :: "a"(code));
    for (;;) __asm__ volatile("pause");
}

BOOLEAN read_captured(UINT32 address, UINT32 *value) {
    ++queries;
    print("SMN "); hex32(address);
    for (UINTN i = 0; i < SMN12_N_READS; ++i) {
        UINT32 addr = (i < SMN12_PAGE_N) ? SMN12_PAGE_BASE + 4U * i
                      : (i < SMN12_I_FAM) ? SMN12_NBIO_BASE + 4U * (i - SMN12_I_NBIO)
                      : /* family block: 5 bases x 16 dwords; base table matches capture_format.h */
                        ((const UINT32[]){0x03800000U,0x03820000U,0x03830000U,0x03840000U,0x03850000U})
                        [(i - SMN12_I_FAM) / SMN12_FAM_N] + 4U * ((i - SMN12_I_FAM) % SMN12_FAM_N);
        if (addr == address) {
            *value = sample.log.Raw[i];
            print(" MEASURED "); hex32(*value); print("\n");
            return TRUE;
        }
    }
    missing = TRUE;
    print(" NOT_CAPTURED\n");
    return FALSE;
}

EFI_STATUS EFIAPI ReplayMain(EFI_HANDLE image, EFI_SYSTEM_TABLE *st) {
    EFI_LOADED_IMAGE_PROTOCOL *loaded;
    EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *volume;
    EFI_FILE_PROTOCOL *root, *file;
    EFI_GUID li = EFI_LOADED_IMAGE_PROTOCOL_GUID, fs = EFI_SIMPLE_FILE_SYSTEM_PROTOCOL_GUID;
    EFI_BOOT_SERVICES *bs = st->BootServices;
    if (EFI_ERROR(bs->HandleProtocol(image, &li, (VOID **)&loaded)) ||
        EFI_ERROR(bs->HandleProtocol(loaded->DeviceHandle, &fs, (VOID **)&volume)) ||
        EFI_ERROR(volume->OpenVolume(volume, &root))) stop(4);
    EFI_STATUS s = root->Open(root, &file, L"A2.BIN", EFI_FILE_MODE_READ, 0);
    root->Close(root);
    if (EFI_ERROR(s)) stop(4);
    UINTN size = sizeof(sample);
    s = file->Read(file, &size, &sample);
    file->Close(file);
    if (EFI_ERROR(s) || size != sizeof(UINT32) + sizeof(sample.log) ||
        sample.attrs != 6 || sample.log.Magic != SMN12_MAGIC ||
        sample.log.Version != SMN12_VERSION || sample.log.Phase != 1 ||
        sample.log.ReadsOk != SMN12_N_READS) stop(4);
    print("REPLAY A2 (RC1 base), DXE entry, board capture\n");
    BOOLEAN ok = probe_check();
    if (missing || !queries) { print("INCONCLUSIVE\n"); stop(2); }
    if (!ok) { print("FAIL\n"); stop(1); }
    print("PASS\n"); stop(0);
}
