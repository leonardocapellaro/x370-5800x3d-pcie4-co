/* capture_format.h — wire format of an A2-style SMN map capture (docs/08).

   A capture is the payload of the probe's volatile EFI variable, saved to a
   file named A2.BIN (the name comes from campaign flash "A2" — the first
   full-aperture map, task 36; your own captures may use any name as long as
   the tools that open it agree). Layout:

     file:   u32 attributes (6 = BS|RT, as stored by the firmware)
             SMN_LOG  (4800 B — the packed struct below)
             optional trailing padding (efivarfs adds attribute bytes)
     Raw[]:  1168 little-endian dwords in FIXED spec order, one read each:
        B2  SMN page      Raw[0..1023]    = 0x03b10000+4*i
        B3a NBIO block    Raw[1024..1087] = 0x03810000+4*i (witness 0x03810054)
        B3b NBIO family   Raw[1088..1167] = 16 dwords each (+0000..+003c) of
                          0x03800000, 0x03820000, 0x03830000, 0x03840000, 0x03850000
     The QCB ternary (0x03b10700/0704/0718) and the four A1 mailbox controls
     (0x03b10524/570/a40/530) are NOT extra reads — they are extracted from
     the B2 page words above (the independent reader recomputes them the same
     way). WritesAttempted must be 0 on any honest capture.

   This schema reproduces the campaign capture byte-for-byte (the bench's
   independent decoder cross-checked every field). Captures are board reads,
   NOT shipped in this repo — build your own probe with tools/probes/ and dump
   the variable to recreate one. */
#ifndef CAPTURE_FORMAT_H
#define CAPTURE_FORMAT_H
#include "uefi_shim.h"

#define SMN12_MAGIC   0x32314d53U    /* 'S','M','1','2' little-endian (version field distinguishes) */
#define SMN12_VERSION 2U             /* three-block wire (page + NBIO + family) */

/* SMN access window pair proven on the board: index latch at host-bridge
 * config offset 0x60, data window at 0x64 (index cycle ONLY, never data). */
#define SMN12_IDX_LATCH 0x80000060U  /* = S_CFG(0,0,0,0x60) */
#define SMN12_DAT_WIN   0x80000064U  /* = S_CFG(0,0,0,0x64) */

#define SMN12_PAGE_BASE 0x03b10000U  /* B2: whole SMN page */
#define SMN12_PAGE_N    1024U
#define SMN12_NBIO_BASE 0x03810000U  /* B3a: NBIO inventory block */
#define SMN12_NBIO_N    64U
#define SMN12_FAM_N     16U           /* B3b: 16 dwords per family base (5 bases) */
#define SMN12_N_READS   (SMN12_PAGE_N+SMN12_NBIO_N+5U*SMN12_FAM_N) /* =1168 */
#define SMN12_I_PAGE 0U
#define SMN12_I_NBIO SMN12_PAGE_N                   /* 1024 */
#define SMN12_I_FAM  (SMN12_PAGE_N+SMN12_NBIO_N)    /* 1088 */
#define NB_IDX(a) ((UINT32)((a)-SMN12_NBIO_BASE)/4U)

/* zones (the spec's operational classification): FF / zero / value */
#define S12A_ZONE_FF 0U
#define S12A_ZONE_ZERO 1U
#define S12A_ZONE_VAL 2U

#pragma pack(push,1)
typedef struct {
  UINT32 Magic,Version,Result,Phase;          /* Phase=1: read at DXE entry (only phase) */
  UINT32 BootCnt,ReadsPlanned,ReadsOk,WritesAttempted; /* ReadsPlanned=1168; WritesAttempted: sentinel — only 0 is valid */
  UINT32 LatchEchoOk,Cf8EchoOk,Flags,NonFFCtl;/* Flags: M1–M4 matrix + witness; NonFFCtl: of the 4 mailbox controls */
  UINT32 PortInCnt,PortOutCnt,ZoneFF,Zone0;   /* port-op audit (5840/7008); zones of the page block (1024) */
  UINT32 ZoneVal,NbioNonFF,FamNonFF,Spare;    /* value zones; !=FF in 0x03810000..ff (max 64) and family (max 80) */
  UINT32 CtlPos[4];                           /* 0x03b10524, 0x03b10570, 0x03b10a40, 0x03b10530 (from the page) */
  UINT32 Ternary[3];                          /* 0x03b10700, 0x03b10704, 0x03b10718 (from the page) */
  UINT32 Reserved[5];
  UINT32 Raw[SMN12_N_READS];                  /* LE raw in spec order: page, NBIO64, family (5x16) */
} SMN_LOG;
#pragma pack(pop)
_Static_assert(sizeof(SMN_LOG)==1200*4,"A2 capture wire is 1200 words (4800 B)");
_Static_assert(sizeof(SMN_LOG)%8==0,"aligned");
/* Raw[] starts at word 32 (byte 128 of the struct; 132 into the file). */

#pragma pack(push,1)
typedef struct {UINT32 Magic,Version,BootCnt,Reserved;} SMN_CNT; /* 16 B, the probe's NV boot counter */
#pragma pack(pop)
_Static_assert(sizeof(SMN_CNT)==16,"16-byte NV counter");

#endif
