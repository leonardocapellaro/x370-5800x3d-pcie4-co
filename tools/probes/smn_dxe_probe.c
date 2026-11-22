/* smn_dxe_probe.c — READ-ONLY SMN probe skeleton for a UEFI DXE driver.

What it is
  A minimal, self-contained skeleton of the DXE-side "SMN sondinha" we flashed
  many times (tasks 35–37/47 era, docs/08): one DXE driver that walks a small
  table of SMN addresses through the CF8/CFC index pair on the AMD host
  bridge (00:00.0 config offsets 0x60 = index latch, 0x64 = data window),
  classifies each dword (all-FF / zero / value), runs a tiny result matrix,
  and exports the raw log in a volatile BootServices|RuntimeServices EFI
  variable, with a separate tiny 16-byte NV variable holding only a boot
  counter.

Why this exact shape
  The house doctrine, proven on the board (every rule below was a measured
  requirement, docs/08 and docs/10):
   * ZERO data writes. The ONLY writes are to the index latch (addresses,
     never data) and to our own log variable. OUT to 0xcfc happens ONLY while
     CF8 points at the INDEX window (0x80000060); the DATA window (0x80000064)
     is IN-only. There is deliberately no write function anywhere in this file;
     the sentinel `WritesAttempted` is copied into the log and must be 0.
   * Save/restore. The previous CF8 value and the previous latch contents are
     read back and restored after every access (pre-read, never assumed).
   * Echoes, not trust. Each read carries two echo bits: bit0 = "wrote CF8 and
     re-read the same value" (the literal 'write CF8, read CF8 = index echo'
     doctrine), bit1 = latch content == address written. Without echoes the
     read is just a hope.
   * Anti-hang by construction: straight-line fixed-cost reads, 5 IN + 6 OUT
     port operations each, no spin, no unbounded loop.
   * The log is volatile (BS|RT, no NV): writing kilobytes to NVRAM every boot
     punishes the SPI chip. Only the 16-byte boot counter is NV.
   * Keep LIVE CONTROLS in every table: a page reading all-FF while the
     controls are alive means "outside this aperture" (a real negative, docs/10
     M22), NOT "dead primitive". All-FF controls mean YOUR probe is broken —
     diagnose before touching the flash again.
  The matrix below mirrors the campaign's M1–M4 precedence verbatim (dead
  first — a dead probe is not science), on a miniature address set:
    DEAD  (M3): any of the 4 controls == FF        -> diagnose, do not re-flash
    LIVE  (M1): ternary fully OUT of the FF zone   -> the mailbox-like row is
            reachable; in the campaign this authorized SPECIING an echoable
            write CAP (never built blindly — docs/05)
    OUT   (M2): ternary entirely IN the FF zone    -> route dead, MEASURED
    INDEF (M4): partial ternary                    -> log, do not decide

The table below is a small REPRESENTATIVE set (page mailbox controls + the QCB
ternary + NBIO witnesses + a negative). The campaign's full maps — e.g. the
148-address NBIO map 0x03810000..00fc + family 0x0380/0382/0383/0384/0385 +
mailbox controls, or the full 1 KiB pages — are described in docs/08;
regenerate them the same way (one address per line, all reads). Nothing about
the probe depends on table size; the capture wire of the full map is in
tools/qemu/capture_format.h.

Build
  * Inside an EDK2 tree: define USE_EDK2_HEADERS, add a .inf of type
    DXE_DRIVER with entry point `SmnProbeEntry` and this single source file,
    put the driver in your DSC/FDF, then `build -a X64 -t GCC5`.
  * Standalone syntax check (no EDK2 needed; -fshort-wchar makes L"..." CHAR16):
        gcc -fsyntax-only -fshort-wchar smn_dxe_probe.c
    The `#else` branch below provides the minimal UEFI type stand-ins so the
    file can be syntax-checked anywhere gcc runs (x86 host assumed).

Read the result after booting (volatile — read BEFORE reboot; owner's step,
root): hexdump /sys/firmware/efi/efivars/BiosmodProbeLog-<your-guid>
*/
#ifdef USE_EDK2_HEADERS
#include <PiDxe.h>
#else
/* Minimal stand-ins for -fsyntax-only (real definitions come from PiDxe.h). */
typedef unsigned char      UINT8;
typedef unsigned short     UINT16;
typedef unsigned int       UINT32;
typedef unsigned long long UINT64;
typedef unsigned long      UINTN;
typedef long               INTN;
typedef void               VOID;
typedef unsigned short     CHAR16;
typedef void              *EFI_HANDLE;
typedef unsigned long      EFI_STATUS;
typedef struct { UINT32 Data1; UINT16 Data2; UINT16 Data3; UINT8 Data4[8]; } EFI_GUID;
#define EFIAPI
#define EFI_SUCCESS                ((EFI_STATUS)0)
#define EFI_VARIABLE_NON_VOLATILE  0x00000001U
#define EFI_VARIABLE_BOOTSERVICE_ACCESS 0x00000002U
#define EFI_VARIABLE_RUNTIME_ACCESS 0x00000004U
typedef struct {
  EFI_STATUS (EFIAPI *GetVariable)(CHAR16 *Name, EFI_GUID *Guid, UINT32 *Attr, UINTN *Size, VOID *Data);
  EFI_STATUS (EFIAPI *SetVariable)(CHAR16 *Name, EFI_GUID *Guid, UINT32 Attr, UINTN Size, VOID *Data);
} EFI_RUNTIME_SERVICES;
typedef struct { EFI_RUNTIME_SERVICES *RuntimeServices; } EFI_SYSTEM_TABLE;
#endif

/* ---- SMN access pair proven on the board: index latch / data window ------- */
#define SMN_IDX_LATCH 0x80000060U  /* = S_CFG(0,0,0,0x60) */
#define SMN_DAT_WIN   0x80000064U  /* = S_CFG(0,0,0,0x64) */

#ifndef SMN_IN
static UINT32 s_in(UINT16 P){UINT32 V;__asm__ volatile("inl %w1,%0":"=a"(V):"d"(P));return V;}
#define SMN_IN(P) s_in(P)
#endif
#ifndef SMN_OUT
static VOID s_out(UINT16 P,UINT32 V){__asm__ volatile("outl %0,%w1"::"a"(V),"d"(P));}
#define SMN_OUT(P,V) s_out(P,V)
#endif

/* Global sentinel: ATTEMPTS of data writes. This module NEVER defines any path
 * that increments it — the existence proof of ZERO-WRITE. Our host suite
 * flags any OUT to CFC while CF8 sits in the data window. */
static volatile UINT32 s_writes_attempted=0U;
/* Anti-hang audit: port operations performed (bounded and asserted). */
static UINT32 s_port_in=0U,s_port_out=0U;

/* One complete SMN read. Returns the dword read; *IdxEcho is the index-cycle
 * echo mask: bit0 = CF8 written == CF8 re-read (the literal doctrine echo);
 * bit1 = latch content == the address written. Port ops per read are fixed
 * (5 IN + 6 OUT) — a known ceiling (anti-hang). */
static UINT32 smn_read(UINT32 Address,UINT32 *Out,UINT32 *IdxEcho){
  UINT32 Cf8,LatchOld,V,E1,E2;
  s_port_in++;  Cf8=SMN_IN(0xcf8);
  s_port_out++; SMN_OUT(0xcf8,SMN_IDX_LATCH);
  s_port_in++;  E1=(SMN_IN(0xcf8)==SMN_IDX_LATCH)?1U:0U;  /* echo1: write CF8 and RE-READ CF8 */
  s_port_in++;  LatchOld=SMN_IN(0xcfc);                   /* pre-read of the latch (read-only) */
  s_port_out++; SMN_OUT(0xcfc,Address);                   /* INDEX cycle (address, never data) */
  s_port_in++;  E2=(SMN_IN(0xcfc)==Address)?1U:0U;        /* echo2: latch content */
  s_port_out++; SMN_OUT(0xcf8,SMN_DAT_WIN);
  s_port_in++;  V=SMN_IN(0xcfc);                          /* THE READ — data window: IN only */
  s_port_out++; SMN_OUT(0xcf8,SMN_IDX_LATCH);
  s_port_out++; SMN_OUT(0xcfc,LatchOld);                  /* restore latch (previous read value) */
  s_port_out++; SMN_OUT(0xcf8,Cf8);                       /* restore previous CF8 */
  *Out=V; if(IdxEcho)*IdxEcho=(E1?1U:0U)|(E2?2U:0U);
  return V;
}

/* ---- representative read table (see docs/08 for the campaign maps) -------- */
#define CTL_N 4U    /* entries [0..3]: the live mailbox controls */
#define TER_N 3U    /* entries [4..6]: the QCB ternary (ARG/STATUS/CMD) */
#define N_ADDR 10U
static const UINT32 kAddrs[N_ADDR]={
  0x03b10524U, /* ctrl: host CMD   (queue 1) — live control */
  0x03b10570U, /* ctrl: host RSP   (queue 1) — live control */
  0x03b10a40U, /* ctrl: host ARG   (queue 1) — live control */
  0x03b10530U, /* ctrl: CMD slot 0             — live control */
  0x03b10700U, /* ternary: ARG  (PSP queue box entry) */
  0x03b10704U, /* ternary: STATUS                   */
  0x03b10718U, /* ternary: CMD                      */
  0x03810000U, /* NBIO block head        */
  0x03810054U, /* NBIO policy proxy witness (inventory flag, never decides) */
  0x03b10ff0U, /* negative control (expected FF/0)  */
};

/* ---- exported log (packed, 4-byte words; wire identical across builds) ---- */
#define PROBE_MAGIC   0x474f5250U   /* 'P','R','O','G' little-endian */
#define PROBE_VERSION 1U
#define ZONE_FF 0U
#define ZONE_ZERO 1U
#define ZONE_VAL 2U
/* results — same precedence as the campaign M1–M4 matrix (docs/08): */
#define RESULT_DEAD  1U /* a control == FF: probe dead, NOT science (M3) — diagnose before reflash */
#define RESULT_LIVE  2U /* ternary fully outside FF: mailbox-like row reachable (M1) */
#define RESULT_OUT   3U /* ternary entirely FF: not reachable via this aperture (M2) — measured negative */
#define RESULT_INDEF 4U /* partial ternary: log, do not decide (M4) */
#define F_WITNESS    0x00000010U /* NBIO witness != FF — inventory audit only, NEVER decides */
#pragma pack(push,1)
typedef struct {
  UINT32 Magic,Version,Result,Phase;          /* Phase=1: read at DXE entry */
  UINT32 BootCnt,ReadsPlanned,ReadsOk,WritesAttempted; /* sentinel must be 0 */
  UINT32 LatchEchoOk,Cf8EchoOk,Flags,NonFFCtl;/* Flags: RESULT_* | F_WITNESS; NonFFCtl: of the 4 controls */
  UINT32 PortInCnt,PortOutCnt,ZoneFF,Zone0;   /* anti-hang audit; zones (page-ish block) */
  UINT32 ZoneVal,Tva,Tff;
  UINT32 Spare[4];                            /* pad: whole wire is a multiple of 8 words */
  UINT32 CtlPos[CTL_N], Ternary[TER_N];       /* convenience copies of the raws */
  UINT32 Raw[N_ADDR];
} PROBE_LOG;
#pragma pack(pop)
_Static_assert(sizeof(PROBE_LOG)%8==0,"8-byte aligned wire");

static VOID memzero(VOID *D,UINTN N){UINTN I;for(I=0;I<N;I++)((UINT8 *)D)[I]=0;}

static VOID run(PROBE_LOG *L){
  UINTN I;UINT32 V,Ok=0U;
  L->ReadsPlanned=N_ADDR;
  for(I=0;I<N_ADDR;I++){
    V=smn_read(kAddrs[I],&V,&Ok);
    L->Raw[I]=V;
    L->ReadsOk++;
    if(Ok&1U)L->Cf8EchoOk++;
    if(Ok&2U)L->LatchEchoOk++;
    if(V==0xffffffffU)L->ZoneFF++;
    else if(V==0U)L->Zone0++;
    else L->ZoneVal++;
  }
  for(I=0;I<CTL_N;I++){
    L->CtlPos[I]=L->Raw[I];
    if(L->CtlPos[I]!=0xffffffffU)L->NonFFCtl++;
  }
  for(I=0;I<TER_N;I++){
    L->Ternary[I]=L->Raw[CTL_N+I];
    if(L->Ternary[I]==0xffffffffU)L->Tff++;else L->Tva++;
  }
  if(L->Raw[8]!=0xffffffffU)L->Flags|=F_WITNESS;   /* inventory only */
  /* matrix — DEAD first (a dead probe is not science), exactly like M3 first */
  if(L->NonFFCtl!=CTL_N){
    L->Flags|=RESULT_DEAD;  L->Result=RESULT_DEAD;   /* diagnose before ANY re-flash */
  }else if(L->Tva==TER_N){
    L->Flags|=RESULT_LIVE;  L->Result=RESULT_LIVE;   /* reachable row: write-CAP may now be SPECIATED */
  }else if(L->Tff==TER_N){
    L->Flags|=RESULT_OUT;   L->Result=RESULT_OUT;    /* route dead with measurement */
  }else{
    L->Flags|=RESULT_INDEF; L->Result=RESULT_INDEF;  /* partial: log, do not decide */
  }
  L->WritesAttempted=s_writes_attempted;      /* sentinel: may only ever be 0 */
  L->PortInCnt=s_port_in;
  L->PortOutCnt=s_port_out;
}

/* ---- variable namespace. GENERATE your own GUIDs (e.g. `uuidgen`) and sweep
 * the base image byte-for-byte for collisions before use, as we did. ------- */
#define PROBE_VAR_GUID {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb}}
#define PROBE_CNT_GUID {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbc}}
#define CNT_MAGIC 0x544e4f43U                 /* 'C','O','N','T' little-endian */
#define CNT_VERSION 1U
#pragma pack(push,1)
typedef struct {UINT32 Magic,Version,BootCnt,Reserved;} PROBE_CNT; /* 16 B, the only NV */
#pragma pack(pop)
_Static_assert(sizeof(PROBE_CNT)==16,"16-byte NV counter");

static EFI_SYSTEM_TABLE *St;
static EFI_GUID ProbeGuid=PROBE_VAR_GUID;
static EFI_GUID ProbeCntGuid=PROBE_CNT_GUID;
static CHAR16 ProbeSlot[]=L"BiosmodProbeLog";      /* volatile BS|RT */
static CHAR16 ProbeCntSlot[]=L"BiosmodProbeCnt";   /* the only NV (16 B) */

/* log lives in BSS: NEVER on the stack — entry stack cost near zero */
static PROBE_LOG probe_log;

/* boot counter: a SEPARATE tiny NV variable — the log is NOT NV */
static UINT32 bootcnt(PROBE_CNT *Next){
  PROBE_CNT Prev;UINTN Sz=sizeof(Prev);
  memzero(&Prev,sizeof(Prev));
  Next->Magic=CNT_MAGIC;Next->Version=CNT_VERSION;Next->Reserved=0U;
  if(St->RuntimeServices->GetVariable(ProbeCntSlot,&ProbeCntGuid,0,&Sz,&Prev)==EFI_SUCCESS&&
     Sz==sizeof(Prev)&&Prev.Magic==CNT_MAGIC&&Prev.Version==CNT_VERSION&&
     Prev.BootCnt<0xfffffff0U){Next->BootCnt=Prev.BootCnt+1U;return Prev.BootCnt+1U;}
  Next->BootCnt=0U;return 0U;
}

EFI_STATUS EFIAPI SmnProbeEntry(EFI_HANDLE Image,EFI_SYSTEM_TABLE *SystemTable){
  PROBE_CNT C;
  (void)Image;
  St=SystemTable;
  memzero(&probe_log,sizeof(probe_log));
  probe_log.Magic=PROBE_MAGIC;probe_log.Version=PROBE_VERSION;probe_log.Phase=1;
  probe_log.BootCnt=bootcnt(&C);
  run(&probe_log);
  St->RuntimeServices->SetVariable(ProbeSlot,&ProbeGuid,
    EFI_VARIABLE_BOOTSERVICE_ACCESS|EFI_VARIABLE_RUNTIME_ACCESS,   /* BS|RT, NO NV */
    sizeof(probe_log),&probe_log);
  St->RuntimeServices->SetVariable(ProbeCntSlot,&ProbeCntGuid,
    EFI_VARIABLE_NON_VOLATILE|EFI_VARIABLE_BOOTSERVICE_ACCESS|EFI_VARIABLE_RUNTIME_ACCESS,
    sizeof(C),&C);                      /* the only NV written: the 16 B counter */
  return EFI_SUCCESS;                   /* never hangs, never retries, nothing to keep */
}
