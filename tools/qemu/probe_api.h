/* probe_api.h — the API a probe author implements/tests against (docs/14).
   Compile your probe logic ONCE and use it in both worlds: here in the QEMU
   replay (reads served from the archived capture) and, adapted at the read
   point, in the real probe module that collects on the board. */
#ifndef C6H_REPLAY_PROBE_API_H
#define C6H_REPLAY_PROBE_API_H
#include "uefi_shim.h"
/* Returns FALSE for an address absent from the reference boot. */
BOOLEAN read_captured(UINT32 address, UINT32 *value);
/* Return TRUE when the probe's assertions hold. Missing reads take precedence. */
BOOLEAN probe_check(VOID);
#endif
