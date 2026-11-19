# SPDX-License-Identifier: GPL-3.0-or-later
"""Host-side tests for actual helper code; not a UEFI/hardware test."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "refind/menu.c").read_text()
helpers = source[source.index("static EG_IMAGE *SplitImages"):source.index("// Display main menu in graphics mode", source.index("static EG_IMAGE *SplitImages"))]
prefix = r'''
#include <assert.h>
#include <stdlib.h>
#include <wchar.h>
typedef unsigned long UINTN;
typedef int BOOLEAN;
typedef void VOID;
typedef wchar_t CHAR16;
#define TRUE 1
#define FALSE 0
typedef struct { UINTN Width, Height; } EG_IMAGE;
typedef struct { int Row; CHAR16 *Title; } ENTRY;
typedef struct { UINTN EntryCount; ENTRY **Entries; } REFIT_MENU_SCREEN;
UINTN UGAWidth=1920, UGAHeight=1080;
void *SelfDir;
int loads, fail_load, fail_scale, allocated;
CHAR16 *MyStrStr(CHAR16 *a, CHAR16 *b) { return wcsstr(a,b); }
void egFreeImage(EG_IMAGE *p) { allocated--; free(p); }
EG_IMAGE *egLoadImage(void *dir, CHAR16 *name, int alpha) {
    if (++loads == fail_load) return NULL;
    EG_IMAGE *p=malloc(sizeof(*p)); allocated++;
    p->Width=1920; p->Height=1080; return p;
}
EG_IMAGE *egScaleImage(EG_IMAGE *p, UINTN w, UINTN h) {
    if (fail_scale) return NULL;
    EG_IMAGE *out=malloc(sizeof(*out)); allocated++;
    out->Width=w; out->Height=h; return out;
}
'''
suffix = r'''
int main(void) {
    ENTRY a={0,L"Boot Windows from SYSTEM"}, b={0,L"Boot Batocera from BATOCERA"};
    ENTRY *entries[]={&a,&b};
    REFIT_MENU_SCREEN screen={2,entries};
    LoadSplitImages(&screen);
    assert(SplitActive && allocated==2);
    FreeSplitImages();
    assert(!SplitActive && allocated==0);
    loads=0; fail_load=2;
    LoadSplitImages(&screen);
    assert(!SplitActive && allocated==0);
    fail_load=0; UGAWidth=1024; UGAHeight=768;
    LoadSplitImages(&screen);
    assert(SplitActive && allocated==2 && SplitImages[0]->Width==1024);
    FreeSplitImages();
    fail_scale=1;
    LoadSplitImages(&screen);
    assert(!SplitActive && allocated==0);
    fail_scale=0;
    screen.EntryCount=1;
    LoadSplitImages(&screen);
    assert(!SplitActive && allocated==0);
    screen.EntryCount=2; a.Title=L"Unexpected";
    LoadSplitImages(&screen);
    assert(!SplitActive && allocated==0);
    a.Title=L"Windows"; b.Row=1;
    LoadSplitImages(&screen);
    assert(!SplitActive && allocated==0);
    return 0;
}
'''
with tempfile.TemporaryDirectory() as folder:
    code = Path(folder) / "test.c"
    code.write_text(prefix + helpers + suffix)
    exe = Path(folder) / "test"
    subprocess.run(["gcc", "-Wall", "-Werror", "-fsanitize=address,undefined", "-g", str(code), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
for width, height in [(1920,1080),(1024,768),(800,600)]:
    boundaries = [(width*1108 - (width*626*y)//height)//1672 for y in range(height)]
    assert all(0 < b < width for b in boundaries)
    assert all(a >= b for a,b in zip(boundaries,boundaries[1:]))
print("PASS: actual image helpers: success, missing image, scaling, allocation failure, invalid menu, cleanup.")
print("PASS: diagonal hit-test bounds at three resolutions. UEFI and physical input remain untested.")
