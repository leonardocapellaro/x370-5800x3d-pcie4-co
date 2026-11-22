/* Minimal harness over the EDK2 REFERENCE code (BaseTools/Source/C/Common):
   proves our Python EFI 1.1 codec (efi11_decompress.py) matches EDK2
   byte-for-byte on the same inputs. Build against an EDK2 checkout, e.g.:
     gcc efitool.c -I <edk2>/BaseTools/Source/C/Include \
         <edk2>/BaseTools/Source/C/Common/Compress.c \
         <edk2>/BaseTools/Source/C/Common/Decompress.c -o efitool
   efitool c <in> <out>  -> EfiCompress   (EFI 1.1, 8-byte header included)
   efitool d <in> <out>  -> EfiGetInfo + EfiDecompress */
#include <stdio.h>
#include <stdlib.h>
#include "Compress.h"
#include "Decompress.h"
static unsigned char *rd(const char *p, UINT32 *n){FILE *f=fopen(p,"rb");if(!f){perror(p);exit(2);}
  fseek(f,0,SEEK_END);long s=ftell(f);fseek(f,0,SEEK_SET);unsigned char *b=malloc(s+16);
  if(fread(b,1,s,f)!=(size_t)s){perror("read");exit(2);}fclose(f);*n=(UINT32)s;return b;}
static void wr(const char *p,const unsigned char *b,UINT32 n){FILE *f=fopen(p,"wb");if(!f){perror(p);exit(2);}
  if(fwrite(b,1,n,f)!=n){perror("write");exit(2);}fclose(f);}
int main(int argc,char **argv){
  if(argc!=4){fprintf(stderr,"usage: efitool c|d in out\n");return 2;}
  UINT32 n;unsigned char *src=rd(argv[2],&n);
  if(argv[1][0]=='c'){
    UINT32 dn=0;EFI_STATUS s=EfiCompress(src,n,NULL,&dn);
    unsigned char *dst=malloc(dn+16);s=EfiCompress(src,n,dst,&dn);
    if(s!=EFI_SUCCESS){fprintf(stderr,"EfiCompress status %lx\n",(unsigned long)s);return 1;}
    wr(argv[3],dst,dn);printf("compress: in=%u out=%u\n",n,dn);return 0;
  }else{
    UINT32 dn=0,sn=0;EFI_STATUS s=EfiGetInfo(src,n,&dn,&sn);
    if(s!=EFI_SUCCESS){fprintf(stderr,"EfiGetInfo status %lx\n",(unsigned long)s);return 1;}
    unsigned char *dst=malloc(dn+16),*scr=malloc(sn+16);
    s=EfiDecompress(src,n,dst,dn,scr,sn);
    if(s!=EFI_SUCCESS){fprintf(stderr,"EfiDecompress status %lx\n",(unsigned long)s);return 1;}
    wr(argv[3],dst,dn);printf("decompress: in=%u out=%u scratch=%u\n",n,dn,sn);return 0;
  }
}
