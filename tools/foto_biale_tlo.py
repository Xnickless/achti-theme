import sys, os
import numpy as np
from PIL import Image, ImageFilter, ImageChops
from rembg import remove, new_session
SRC=sys.argv[1]; OUT=sys.argv[2]; files=sys.argv[3:]
if files and files[0].startswith('@'):
    files=[l.rstrip('\n') for l in open(files[0][1:],encoding='utf-8') if l.strip()]
files=[f for f in files if not os.path.exists(os.path.join(OUT,os.path.splitext(f)[0]+'.jpg'))]
print('do zrobienia:',len(files),flush=True)
session=new_session("isnet-general-use")
SIZE=(2000,2500); PAD=0.07

def bg_level(rgb):
    a=np.asarray(rgb.convert("L"),dtype=np.float32)
    h,w=a.shape; s=int(min(h,w)*0.08)
    corners=np.concatenate([a[:s,:s].ravel(),a[:s,-s:].ravel(),a[-s:,:s].ravel(),a[-s:,-s:].ravel()])
    return float(np.median(corners))

def whiten(rgb, bg):
    lo=max(0,bg-60); hi=max(lo+1,bg-8)
    lut=[]
    for v in range(256):
        if v<=lo: lut.append(v)
        elif v>=hi: lut.append(255)
        else: lut.append(int(round(lo+(v-lo)*(255-lo)/(hi-lo))))
    return rgb.point(lut*3)

def process(path):
    img=Image.open(path).convert("RGB")
    if max(img.size)>3000:
        r=3000/max(img.size); img=img.resize((int(img.width*r),int(img.height*r)),Image.LANCZOS)
    bg=bg_level(img)
    alpha=remove(img, session=session, only_mask=True).convert("L")
    core=alpha.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(3))
    # v3: zamiast szerokiego pierścienia (31 px) z rozjaśnionym tłem — miękka maska z matte,
    # lekko poszerzona (włókna), a poza nią czysta biel; usuwa poświatę/cień nad czapką
    soft=alpha.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(2.5))
    edge_alpha=ImageChops.lighter(core, soft)
    outer=alpha.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(12))
    white=Image.new("RGB",img.size,(255,255,255))
    light=whiten(img,bg)
    edge=Image.composite(light, white, edge_alpha)
    result=Image.composite(img, edge, core)
    bbox=outer.point(lambda a:255 if a>40 else 0).getbbox() or (0,0)+img.size
    crop=result.crop(bbox); w,h=crop.size; tw,th=SIZE
    scale=min((tw*(1-2*PAD))/w,(th*(1-2*PAD))/h)
    crop=crop.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.LANCZOS)
    canvas=Image.new("RGB",SIZE,(255,255,255))
    canvas.paste(crop,((tw-crop.width)//2,(th-crop.height)//2))
    return canvas, bg

for f in files:
    out,bg=process(os.path.join(SRC,f))
    name=os.path.splitext(f)[0]
    out.save(os.path.join(OUT,name+".jpg"),quality=92,optimize=True)
    print(f"ok bg={bg:.0f} {f}",flush=True)
