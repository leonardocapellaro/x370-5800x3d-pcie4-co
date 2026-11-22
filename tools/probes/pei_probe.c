/* pei_probe.c — READ-ONLY PEI probe skeleton (IA32/X64 PEIM).

What it is
  A minimal skeleton of the PEI-stage sondinha (task 46 era, docs/04/docs/08):
  a PEIM entry that (1) grabs platform forensics (CPUID leaf 1, boot mode),
  (2) measures what sits at [IDTR.base-4] — in our boots that held a control
  block whose vtable we wanted to attribute — under explicit address guards,
  reading the block's six fields and its first 32 pointers plus a 1 KiB
  window around it, and (3) UNCONDITIONALLY records the whole register in a
  GUID HOB (create-or-lookup, idempotent). No read, however bad, may prevent
  the HOB: that was the lesson of earlier flashes (nothing may fail before
  the record is written). A companion DXE observer (pattern: ReadyToBoot →
  GetHobList → SetVariable) turns the HOB into an EFI variable; if the
  variable says HOB_MISSING the PEIM was never dispatched — a branch you need
  when the gate under investigation is dispatch itself.

Why this exact shape
  * READ-ONLY ABSOLUTE: no port I/O at all (CF8/CFC never touched here — that
    is the DXE probe's job), no `mov [mem]` outside the register/HOB copy via
    services, no mailbox/SMU/MSR writes, no flash. The only machine-state
    instructions: SIDT (read IDTR), MOV CR0 (read), CPUID.
  * In PEI there is no try/except: EVERY address passes the spec guard
    (peipsane: non-null, non-0xFFFFFFFF, below the device ceiling) BEFORE
    the dereference, and skipped reads are recorded in masks, never faked.
  * The entry is unconditional: measure, record, return EFI_SUCCESS always —
    never interfere with dispatch.
  * Entry 16-byte aligned (the T40 lesson: an odd entry point was a suspect;
    it was later measured NOT to be the gate, docs/10 — keep it aligned anyway).

Build
  * Inside an EDK2 tree: define USE_EDK2_HEADERS, .inf of type PEIM, entry
    point `PeiProbeEntry`, single source. (Where to put it in the dispatch
    order is itself a measured question — see docs/08 §PEI and docs/10 M24.)
  * Standalone syntax check: gcc -fsyntax-only pei_probe.c  (the #else branch
    below is the minimal stand-in; x86 host assumed, IA32 also fine).

Findings it encodes: the [IDTR.base-4] block and the services-table marker;
the PEI_SERVICES_SIGNATURE low dword as a forensic marker (assert below).
*/
#ifdef USE_EDK2_HEADERS
#include <PiPei.h>
#else
/* Minimal stand-ins for -fsyntax-only (real definitions come from PiPei.h). */
typedef unsigned char      UINT8;
typedef unsigned short     UINT16;
typedef unsigned int       UINT32;
typedef unsigned long long UINT64;
typedef unsigned long      UINTN;
typedef long               INTN;
typedef void               VOID;
typedef unsigned char      BOOLEAN;
#define TRUE  1
#define FALSE 0
typedef void              *EFI_HANDLE;
typedef unsigned long      EFI_STATUS;
typedef struct { UINT32 Data1; UINT16 Data2; UINT16 Data3; UINT8 Data4[8]; } EFI_GUID;
typedef UINT32             EFI_BOOT_MODE;
typedef void              *EFI_PEI_FILE_HANDLE;
#define EFIAPI
#define EFI_SUCCESS        ((EFI_STATUS)0)
#define PEI_SERVICES_SIGNATURE 0x5652455320494550ULL   /* "PEI SERV" (PiPeiCis.h) */
typedef struct { UINT64 Signature; UINTN Size; } EFI_PEI_SERVICE_SIGNATURE_HEADER;
typedef struct _EFI_PEI_SERVICES {
  EFI_PEI_SERVICE_SIGNATURE_HEADER Hdr;
  EFI_STATUS (EFIAPI *GetBootMode)(const struct _EFI_PEI_SERVICES **Ps, EFI_BOOT_MODE *Mode);
  EFI_STATUS (EFIAPI *GetHobList)(const struct _EFI_PEI_SERVICES **Ps, VOID **HobList);
  EFI_STATUS (EFIAPI *CreateHob)(const struct _EFI_PEI_SERVICES **Ps, UINT16 Type, UINTN Length, VOID **Hob);
} EFI_PEI_SERVICES;
#define EFI_HOB_TYPE_GUID_EXTENSION 4U
#define EFI_HOB_TYPE_END_OF_HOB_LIST 0xFFFFU
typedef struct { UINT16 HobType; UINT16 HobLength; UINT32 Reserved; } EFI_HOB_GENERIC_HEADER;
typedef struct { EFI_HOB_GENERIC_HEADER Header; EFI_GUID Name; } EFI_HOB_GUID_TYPE;
#endif

#define PEIP_BUILD     0x00000001U
#define PEIP_VERSION   1U
#define PEIP_REC_MAGIC 0x50494550U  /* 'P','E','I','P' little-endian (HOB == variable payload) */

/* low dword of PEI_SERVICES_SIGNATURE — forensic marker: the [IDTR.base-4]
 * block being the PEI services table itself shows up exactly here */
#define PEIP_PS_SIG_LO 0x20494550U
_Static_assert((PEI_SERVICES_SIGNATURE&0xffffffffULL)==PEIP_PS_SIG_LO,
  "low dword of PEI_SERVICES signature matches the forensic marker");

/* GUIDs: GENERATE your own and sweep the base for collisions (docs/08). */
#define PEIP_VAR_GUID {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xcc,0x01}}
#define PEIP_HOB_GUID {0x11111111,0x2222,0x3333,{0x44,0x55,0x66,0x77,0x88,0x99,0xcc,0x02}}

/* 32-bit address guard (pre-memory; sane = non-null, non-FF, below the
 * device ceiling) — spec heuristic, applied to EVERYTHING */
#define PEIP_ADDR_CEIL 0xC0000000U

/* register flags */
#define PEIP_F_CTRL_SANE    0x00000001U /* ctrl passed the spec guard */
#define PEIP_F_IDT_BAD      0x00000002U /* IDTR.base<4 or ctrl read failed */
#define PEIP_F_VT_SANE      0x00000004U /* vtable = [ctrl+0x00] passed the guard */
#define PEIP_F_WIN_FULL     0x00000008U /* whole 1 KiB window readable */
#define PEIP_F_WIN_PART     0x00000010U /* window with skips (WinMask marks them) */
#define PEIP_F_PAGING       0x00000020U /* CR0.PG at entry time */
#define PEIP_F_PROTECTED    0x00000040U /* CR0.PE at entry time */
#define PEIP_F_SERVICES_OK  0x00000080U /* arg services table: PI signature ok */
#define PEIP_F_SERVICES_BAD 0x00000100U /* arg services missing / bad signature */
#define PEIP_F_VT_IS_PSVCS  0x00000200U /* [ctrl+0x00] == PEI_SERVICES sig low dword */
#define PEIP_F_CTRL_EQ_SVCS 0x00000400U /* ctrl == entry services table pointer */

/* HobStatus (DXE fills; 0 = collected) */
#define PEIP_H_OK      0U
#define PEIP_H_AUSENTE 1U /* never dispatched (candidate): no HOB of ours this boot */

#pragma pack(push,1)
/* the whole register (same bytes in HOB and variable payload): 328 dwords;
 * all UINT32 so the layout is identical IA32/X64 */
typedef struct {
  UINT32 Magic,Version,Build;
  UINT32 BootCnt;                    /* 0xFFFFFFFF in the HOB; DXE fills it (prev+1 or 0) */
  UINT32 HobStatus;                  /* DXE fills; 0 in the HOB */
  UINT32 Flags;                      /* above */
  UINT32 IdtLimit,IdtBase,Cr0;       /* IDTR and CR0 measured at entry */
  UINT32 Cpu[4];                     /* CPUID leaf 1 (platform forensics) */
  UINT32 BootMode;
  UINT32 Ctrl;                       /* raw dword at [IDTR.base-4] */
  UINT32 CtrlFields[6];              /* ctrl+0x00/0x34/0x38/0x50/0x54/0x58 (0 when unread) */
  UINT32 VtMask;                     /* bit i = 1 => vtable[i] READ (0 = skipped) */
  UINT32 Vt[32];                     /* vtable dwords from [ctrl+0x00] */
  UINT32 WinBase;                    /* ctrl-0x80 (0 when window not started) */
  UINT32 WinMask[8];                 /* bit = 1 => window dword SKIPPED (guard) */
  UINT32 Win[256];                   /* 1 KiB: ctrl-0x80 .. ctrl+0x37c */
  UINT32 Reserved[9];
} PEIP_REC;
#pragma pack(pop)
_Static_assert(sizeof(PEIP_REC)==328*4,"whole register is 328 words (1312 B)");
_Static_assert(sizeof(PEIP_REC)+24<=65528&&(sizeof(PEIP_REC)+24)%8==0,"PI HOB limits (1336 B)");

/* inline helpers (own domain; no library calls in pre-memory PEI) */
static VOID peipcopy(VOID *D,const VOID *S,UINTN N){UINTN I;for(I=0;I<N;I++)((UINT8 *)D)[I]=((const UINT8 *)S)[I];}
static VOID peipzero(VOID *D,UINTN N){UINTN I;for(I=0;I<N;I++)((UINT8 *)D)[I]=0;}
static BOOLEAN peipguid(const EFI_GUID *A,const EFI_GUID *B){
  UINTN I;for(I=0;I<16;I++)if(((const UINT8 *)A)[I]!=((const UINT8 *)B)[I])return FALSE;return TRUE;}
/* the SPEC GUARD: non-null, non-0xFFFFFFFF, < ceiling */
static BOOLEAN peipsane(UINTN V){return V!=0&&V!=0xffffffffU&&V<PEIP_ADDR_CEIL;}

/* ---- measurement ENGINE (read-only), same code in module and host suite:
 * the read "world" is a function vector — in the module a raw address
 * dereference (pre-memory, no paging, no try/except: that is WHY the engine
 * applies the spec guard BEFORE each access); in the host a modeled map that
 * may deliberately fail. The engine writes ONLY into register R; every read
 * goes through W->Rd32 under the guard; skips are recorded in masks. */
typedef struct {
  /* Read the dword at Addr if fully mapped; return 1 with *V, 0 if unreadable
   * (the WORLD decides; the engine decides whether to ask). */
  UINTN (*Rd32)(const VOID *W,UINTN Addr,UINT32 *V);
} PEIP_WORLD;

/* control-block field offsets measured useful in our boots (docs/08) */
static const UINT32 kPeipFields[6]={0x00U,0x34U,0x38U,0x50U,0x54U,0x58U};

static VOID peip_measure(PEIP_REC *R,const PEIP_WORLD *W,
                         UINT32 IdtLimit,UINTN IdtBase,UINT32 Cr0){
  UINTN I,Ok,Rd=0,RdOk=0;UINT32 V;
  R->Magic=PEIP_REC_MAGIC;R->Version=PEIP_VERSION;R->Build=PEIP_BUILD;
  R->BootCnt=0xffffffffU;              /* 0xFFFFFFFF in the HOB: only DXE knows the boot */
  R->HobStatus=PEIP_H_OK;
  R->Flags=0;
  R->IdtLimit=IdtLimit;R->IdtBase=(UINT32)IdtBase;R->Cr0=Cr0;
  if(Cr0&0x80000000U)R->Flags|=PEIP_F_PAGING;
  if(Cr0&1U)R->Flags|=PEIP_F_PROTECTED;
  if(IdtBase>=4&&peipsane(IdtBase-4U)){
    Rd++;if(W->Rd32(W,IdtBase-4U,&V)){RdOk++;R->Ctrl=V;}else R->Flags|=PEIP_F_IDT_BAD;
    if(peipsane(R->Ctrl)){
      UINT32 Ctrl=R->Ctrl;
      R->Flags|=PEIP_F_CTRL_SANE;
      for(I=0;I<6;I++){
        if(Ctrl+kPeipFields[I]+4U<=PEIP_ADDR_CEIL){
          Rd++;if(W->Rd32(W,Ctrl+kPeipFields[I],&V)){RdOk++;R->CtrlFields[I]=V;}}
      }
      if(R->CtrlFields[0]==PEIP_PS_SIG_LO)R->Flags|=PEIP_F_VT_IS_PSVCS;
      if(peipsane(R->CtrlFields[0])&&R->CtrlFields[0]+32*4U<=PEIP_ADDR_CEIL){
        R->Flags|=PEIP_F_VT_SANE;
        for(I=0;I<32;I++){
          Rd++;if(W->Rd32(W,R->CtrlFields[0]+4U*I,&V)){RdOk++;R->Vt[I]=V;R->VtMask|=1U<<I;}
        }
      }
      if(Ctrl>=0x80U){                 /* raw window ctrl-0x80 .. ctrl+0x37c (1 KiB) */
        UINTN Wb=Ctrl-0x80U;R->WinBase=(UINT32)Wb;
        for(I=0;I<256;I++){
          if(Wb+4U*I+4U<=PEIP_ADDR_CEIL){
            Rd++;if(W->Rd32(W,Wb+4U*I,&V)){RdOk++;R->Win[I]=V;continue;}}
          R->WinMask[I/32]|=1U<<(I%32);
        }
        R->Flags|=R->WinMask[0]|R->WinMask[1]|R->WinMask[2]|R->WinMask[3]|
                  R->WinMask[4]|R->WinMask[5]|R->WinMask[6]|R->WinMask[7]?
                  PEIP_F_WIN_PART:PEIP_F_WIN_FULL;
      }
    }
  }else R->Flags|=PEIP_F_IDT_BAD;
  R->Reserved[0]=(UINT32)Rd;           /* audit: Rd32 requests made by the engine */
  R->Reserved[1]=(UINT32)RdOk;         /* audit: Rd32 requests the world served */
  R->Reserved[2]=0;R->Reserved[3]=0;R->Reserved[4]=0;R->Reserved[5]=0;
  R->Reserved[6]=0;R->Reserved[7]=0;R->Reserved[8]=0;
}

static EFI_GUID PeipHob=PEIP_HOB_GUID;

/* --- REAL world: raw dereference already under the engine's guard
 * (pre-memory, no paging; PEI has no try/except — the GUARD decides first) */
static UINTN EFIAPI peip_rd_raw(const VOID *W,UINTN Addr,UINT32 *V){
  (void)W;
  *V=*(const volatile UINT32 *)(UINTN)Addr;   /* addresses already vetted by peipsane() */
  return 1;}
static const PEIP_WORLD PeipRawWorld={peip_rd_raw};

/* --- state HOB: create-or-lookup (idempotent if dispatched twice) --- */
static PEIP_REC *peip_hob(const EFI_PEI_SERVICES **Ps,BOOLEAN Create){
  EFI_HOB_GENERIC_HEADER *H=0;UINTN I;
  if((*Ps)->GetHobList(Ps,(VOID **)&H)!=EFI_SUCCESS)return 0;
  for(I=0;H&&I<4096;I++){
    if(H->HobType==EFI_HOB_TYPE_END_OF_HOB_LIST)break;
    if(H->HobLength<8||H->HobLength&7)return 0;
    if(H->HobType==EFI_HOB_TYPE_GUID_EXTENSION&&H->HobLength==24+sizeof(PEIP_REC)&&
       peipguid(&((EFI_HOB_GUID_TYPE *)H)->Name,&PeipHob))
      return (PEIP_REC *)((UINT8 *)H+24);}
  if(!Create||I==4096||
     (*Ps)->CreateHob(Ps,4,24+sizeof(PEIP_REC),(VOID **)&H)!=EFI_SUCCESS||!H)return 0;
  peipcopy(&((EFI_HOB_GUID_TYPE *)H)->Name,&PeipHob,16);
  return (PEIP_REC *)((UINT8 *)H+24);}

__attribute__((aligned(16)))   /* house pattern: 16-aligned entry (even EP) */
EFI_STATUS EFIAPI PeiProbeEntry(EFI_PEI_FILE_HANDLE File,const EFI_PEI_SERVICES **Ps){
  PEIP_REC R;PEIP_REC *H;
  struct {UINT16 Limit;UINT32 Base;} __attribute__((packed)) Idt;
  UINT32 Cr0=0;EFI_BOOT_MODE Mode=0;
  (void)File;
  /* 1) zeroed register on the stack (1312 B; fine for the PEI stack — never
   *    in BSS so the module stays small; written ONCE into the HOB) */
  peipzero(&R,sizeof(R));
  /* 2) platform forensics and boot mode (never blocking) */
  __asm__ volatile("cpuid":"=a"(R.Cpu[0]),"=b"(R.Cpu[1]),"=c"(R.Cpu[2]),"=d"(R.Cpu[3]):"a"(1));
  if(Ps&&*Ps&&(*Ps)->Hdr.Signature==PEI_SERVICES_SIGNATURE){
    R.Flags|=PEIP_F_SERVICES_OK;
    if((*Ps)->GetBootMode&&(*Ps)->GetBootMode(Ps,&Mode)==EFI_SUCCESS)R.BootMode=(UINT32)Mode;
  }else R.Flags|=PEIP_F_SERVICES_BAD;
  /* 3) measurement: IDTR + CR0 (reads) -> engine with guards/masks */
  __asm__ volatile("sidt %0":"=m"(Idt));
  __asm__ volatile("mov %%cr0,%0":"=a"(Cr0));
  peip_measure(&R,&PeipRawWorld,Idt.Limit,(UINTN)Idt.Base,Cr0);
  /* 4) forensic marker: is the [IDTR.base-4] block the services table itself? */
  if((R.Flags&PEIP_F_SERVICES_OK)&&R.Ctrl==(UINT32)(UINTN)*Ps)
    R.Flags|=PEIP_F_CTRL_EQ_SVCS;
  /* 5) UNCONDITIONAL write of the register into the HOB (even on bad branches) */
  if(Ps&&*Ps&&(*Ps)->Hdr.Signature==PEI_SERVICES_SIGNATURE&&(*Ps)->GetHobList&&
     (*Ps)->CreateHob){
    H=peip_hob(Ps,TRUE);
    if(H)peipcopy(H,&R,sizeof(R));}
  return EFI_SUCCESS;}                    /* always: never interfere with dispatch */
