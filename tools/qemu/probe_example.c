#include "probe_api.h"

/* Example of the decision logic shared with a data-collecting probe:
   consult the archived capture, assert on the value. Run it with
   replay_run.py --probe probe_example.c (docs/14). */
BOOLEAN probe_check(VOID) {
    UINT32 value;
    return read_captured(0x03810054, &value) && value == 1;
}
