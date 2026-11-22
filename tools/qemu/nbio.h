/* nbio.h — live SMN read of the NBIO block through PciIo (LIVE bench mode).
   Same index/data pair (host-bridge config offsets 0x60/0x64) as the CF8
   probe, expressed through the DXE PciIo protocol so the platform firmware
   mediates it. Save/restore + echo checks mirror the CF8 doctrine exactly.
   docs/08 describes the campaign's use; docs/10 why only reads belong here. */
#ifndef NBIO_H
#define NBIO_H
#include "uefi_shim.h"

#define NBIO_BASE 0x03810000U
#define NBIO_COUNT 64U

static BOOLEAN known_address(UINT32 address) {
    return address >= NBIO_BASE && address < NBIO_BASE + 4 * NBIO_COUNT && !(address & 3);
}

static EFI_STATUS read_nbio(EFI_PCI_IO_PROTOCOL *pci, UINT32 address, UINT32 *value) {
    UINT32 saved, selected;
    EFI_STATUS status, restored;
    if (!known_address(address)) return EFI_INVALID_PARAMETER;
    status = pci->Pci.Read(pci, EfiPciIoWidthUint32, 0x60, 1, &saved);
    if (EFI_ERROR(status)) return status;
    status = pci->Pci.Write(pci, EfiPciIoWidthUint32, 0x60, 1, &address);
    if (!EFI_ERROR(status)) status = pci->Pci.Read(pci, EfiPciIoWidthUint32, 0x60, 1, &selected);
    if (!EFI_ERROR(status) && selected != address) status = EFI_DEVICE_ERROR;
    if (!EFI_ERROR(status)) status = pci->Pci.Read(pci, EfiPciIoWidthUint32, 0x64, 1, value);
    restored = pci->Pci.Write(pci, EfiPciIoWidthUint32, 0x60, 1, &saved);
    if (!EFI_ERROR(restored)) restored = pci->Pci.Read(pci, EfiPciIoWidthUint32, 0x60, 1, &selected);
    if (EFI_ERROR(restored) || selected != saved) return EFI_DEVICE_ERROR;
    return status;
}
#endif
