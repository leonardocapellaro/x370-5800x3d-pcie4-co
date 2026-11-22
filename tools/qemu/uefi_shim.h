/* uefi_shim.h — minimal UEFI stand-ins so the bancada C sources pass
   `gcc -fsyntax-only` outside an EDK2 tree (x86 host).

   Define USE_EDK2_HEADERS and compile against an EDK2 checkout (see
   docs/14 and replay_run.py) to get the real headers instead. In shim mode
   the protocol GUID "constants" below are PLACEHOLDER values for syntax
   checking only — the real build takes the true GUIDs from EDK2. */
#ifndef UEFI_SHIM_H
#define UEFI_SHIM_H

#ifdef USE_EDK2_HEADERS
#include <Uefi.h>
#include <Protocol/LoadedImage.h>
#include <Protocol/SimpleFileSystem.h>
#include <Protocol/PciIo.h>
#else

typedef unsigned char      UINT8;
typedef unsigned short     UINT16;
typedef unsigned int       UINT32;
typedef unsigned long long UINT64;
typedef unsigned long      UINTN;
typedef long               INTN;
typedef void               VOID;
typedef char               CHAR8;
typedef unsigned short     CHAR16;
typedef unsigned char      BOOLEAN;
#define TRUE  1
#define FALSE 0
typedef void              *EFI_HANDLE;
typedef unsigned long      EFI_STATUS;
typedef unsigned long      EFI_TPL;
typedef struct { UINT32 Data1; UINT16 Data2; UINT16 Data3; UINT8 Data4[8]; } EFI_GUID;
#define EFIAPI
#ifndef NULL
#define NULL ((void *)0)
#endif
#define EFI_ERROR(x)   (((INTN)(EFI_STATUS)(x)) < 0)
#define EFI_SUCCESS    ((EFI_STATUS)0)
/* numeric values are placeholders for syntax checking (real ones: EDK2) */
#define EFI_INVALID_PARAMETER  ((EFI_STATUS)0x8000000000000002ULL)
#define EFI_UNSUPPORTED        ((EFI_STATUS)0x8000000000000003ULL)
#define EFI_DEVICE_ERROR       ((EFI_STATUS)0x8000000000000007ULL)
#define EFI_NOT_FOUND          ((EFI_STATUS)0x800000000000000EULL)
#define EFI_VOLUME_FULL        ((EFI_STATUS)0x8000000000000020ULL)
#define EFI_COMPROMISED_DATA   ((EFI_STATUS)0x8000000000000024ULL)

#define EFI_FILE_MODE_READ   0x0000000000000001ULL
#define EFI_FILE_MODE_WRITE  0x0000000000000002ULL
#define EFI_FILE_MODE_CREATE 0x8000000000000000ULL

#define TPL_NOTIFY ((EFI_TPL)16)
typedef enum { AllHandles = 1, ByRegisterNotify = 2, ByProtocol = 3 } EFI_LOCATE_SEARCH_TYPE;

/* forward typedefs so function-pointer parameters see real tags */
typedef struct EFI_FILE_PROTOCOL EFI_FILE_PROTOCOL;
typedef struct EFI_SIMPLE_FILE_SYSTEM_PROTOCOL EFI_SIMPLE_FILE_SYSTEM_PROTOCOL;
typedef struct _EFI_PCI_IO_PROTOCOL EFI_PCI_IO_PROTOCOL;

typedef struct EFI_FILE_PROTOCOL {
  UINT64 Revision;
  EFI_STATUS (EFIAPI *Open)(struct EFI_FILE_PROTOCOL *This, struct EFI_FILE_PROTOCOL **Handle,
                            CHAR16 *FileName, UINT64 OpenMode, UINT64 Attributes);
  EFI_STATUS (EFIAPI *Close)(struct EFI_FILE_PROTOCOL *This);
  EFI_STATUS (EFIAPI *Read)(struct EFI_FILE_PROTOCOL *This, UINTN *BufferSize, VOID *Buffer);
  EFI_STATUS (EFIAPI *Write)(struct EFI_FILE_PROTOCOL *This, UINTN *BufferSize, VOID *Buffer);
  EFI_STATUS (EFIAPI *Flush)(struct EFI_FILE_PROTOCOL *This);
} EFI_FILE_PROTOCOL;

struct EFI_SIMPLE_FILE_SYSTEM_PROTOCOL {
  UINT64 Revision;
  EFI_STATUS (EFIAPI *OpenVolume)(EFI_SIMPLE_FILE_SYSTEM_PROTOCOL *This, EFI_FILE_PROTOCOL **Root);
};

typedef struct {
  UINT32     Revision;
  EFI_HANDLE ParentHandle;
  struct EFI_SYSTEM_TABLE *SystemTable;
  EFI_HANDLE DeviceHandle;
  VOID      *SystemPartition;
  VOID      *FilePath;
} EFI_LOADED_IMAGE_PROTOCOL;

typedef enum { EfiPciIoWidthUint8 = 0, EfiPciIoWidthUint16, EfiPciIoWidthUint32 } EFI_PCI_IO_PROTOCOL_WIDTH;

typedef struct {
  EFI_STATUS (EFIAPI *Read)(EFI_PCI_IO_PROTOCOL *This, EFI_PCI_IO_PROTOCOL_WIDTH Width,
                            UINT32 Offset, UINT32 Count, VOID *Buffer);
  EFI_STATUS (EFIAPI *Write)(EFI_PCI_IO_PROTOCOL *This, EFI_PCI_IO_PROTOCOL_WIDTH Width,
                             UINT32 Offset, UINT32 Count, VOID *Buffer);
} EFI_PCI_IO_PROTOCOL_PCI;

struct _EFI_PCI_IO_PROTOCOL {
  UINT64 Revision;
  EFI_STATUS (EFIAPI *GetLocation)(struct _EFI_PCI_IO_PROTOCOL *This, UINTN *Segment, UINTN *Bus,
                                   UINTN *Device, UINTN *Function);
  EFI_PCI_IO_PROTOCOL_PCI Pci;
};

typedef struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL {
  EFI_STATUS (EFIAPI *OutputString)(struct EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *This, CHAR16 *String);
} EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL;

typedef struct {
  EFI_STATUS (EFIAPI *HandleProtocol)(EFI_HANDLE Handle, EFI_GUID *Protocol, VOID **Interface);
  EFI_STATUS (EFIAPI *LocateHandleBuffer)(EFI_LOCATE_SEARCH_TYPE SearchType, EFI_GUID *Protocol,
                                          VOID *SearchKey, UINTN *NoHandles, EFI_HANDLE **Buffer);
  EFI_STATUS (EFIAPI *FreePool)(VOID *Buffer);
  EFI_TPL    (EFIAPI *RaiseTPL)(EFI_TPL NewTpl);
  VOID       (EFIAPI *RestoreTPL)(EFI_TPL OldTpl);
} EFI_BOOT_SERVICES;

struct EFI_SYSTEM_TABLE {
  EFI_BOOT_SERVICES             *BootServices;
  EFI_SIMPLE_TEXT_OUTPUT_PROTOCOL *ConOut;
};
typedef struct EFI_SYSTEM_TABLE EFI_SYSTEM_TABLE;

/* placeholder GUIDs for -fsyntax-only (real values: EDK2 headers) */
#define EFI_LOADED_IMAGE_PROTOCOL_GUID     {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xdd,0x01}}
#define EFI_SIMPLE_FILE_SYSTEM_PROTOCOL_GUID {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xdd,0x02}}
#define EFI_PCI_IO_PROTOCOL_GUID           {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xdd,0x03}}

#endif /* USE_EDK2_HEADERS */
#endif /* UEFI_SHIM_H */
