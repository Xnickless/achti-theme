"""Edycja wycinka przez Qwen-Image-Edit-2509 lokalnie (ComfyUI na 127.0.0.1:8188, GGUF Q4_K_M + Lightning 8 kroków),
21.10.2026 — do metek, które LaMa zostawił rozmyte na wzorach. Bez kredytów, wszystko na Macu.

  # serwer: cd ~/Claude/achti-foto/ComfyUI && ~/Claude/achti-foto/venv/bin/python3 main.py --port 8188
  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/qwen_edit.py WEJŚCIE.jpg WYJŚCIE.png ["polecenie"] [--mp=1.0] [--kroki=8|4]

Funkcja edit(path_in, path_out, prompt) używana też z innych skryptów.
"""
import json
import os
import shutil
import sys
import time
import urllib.request
import uuid

URL = 'http://127.0.0.1:8188'
COMFY = os.path.expanduser('~/Claude/achti-foto/ComfyUI')
PROMPT = ('Remove the paper hang tag, its string and any sticker or label from the knitted fabric. Reconstruct the knit '
          'underneath so it continues the surrounding stitches, pattern, colours and lighting exactly. Change nothing else.')


def workflow(img_name, prompt, mp, seed, steps=8):
    return {
        '1': {'class_type': 'UnetLoaderGGUF', 'inputs': {'unet_name': 'Qwen-Image-Edit-2509-Q4_K_M.gguf'}},
        '2': {'class_type': 'LoraLoaderModelOnly', 'inputs': {
            'model': ['1', 0], 'lora_name': f'Qwen-Image-Edit-2509-Lightning-{steps}steps-V1.0-bf16.safetensors', 'strength_model': 1.0}},
        '3': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['2', 0], 'shift': 3.0}},
        '4': {'class_type': 'CLIPLoaderGGUF', 'inputs': {'clip_name': 'Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf', 'type': 'qwen_image'}},
        '5': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'qwen_image_vae.safetensors'}},
        '6': {'class_type': 'LoadImage', 'inputs': {'image': img_name}},
        '7': {'class_type': 'ImageScaleToTotalPixels', 'inputs': {'image': ['6', 0], 'upscale_method': 'lanczos', 'megapixels': mp,
                                                                  'resolution_steps': 8}},
        '8': {'class_type': 'TextEncodeQwenImageEditPlus', 'inputs': {'clip': ['4', 0], 'prompt': prompt, 'vae': ['5', 0], 'image1': ['7', 0]}},
        '9': {'class_type': 'TextEncodeQwenImageEditPlus', 'inputs': {'clip': ['4', 0], 'prompt': '', 'vae': ['5', 0], 'image1': ['7', 0]}},
        '10': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['7', 0], 'vae': ['5', 0]}},
        '11': {'class_type': 'KSampler', 'inputs': {'model': ['3', 0], 'positive': ['8', 0], 'negative': ['9', 0], 'latent_image': ['10', 0],
                                                    'seed': seed, 'steps': steps, 'cfg': 1.0, 'sampler_name': 'euler',
                                                    'scheduler': 'simple', 'denoise': 1.0}},
        '12': {'class_type': 'VAEDecode', 'inputs': {'samples': ['11', 0], 'vae': ['5', 0]}},
        '13': {'class_type': 'SaveImage', 'inputs': {'images': ['12', 0], 'filename_prefix': 'qwen_edit'}},
    }


def edit(path_in, path_out, prompt=PROMPT, mp=1.0, seed=7, timeout=3600, steps=8):
    name = f'qe_{uuid.uuid4().hex[:8]}{os.path.splitext(path_in)[1]}'
    shutil.copy(path_in, os.path.join(COMFY, 'input', name))
    body = json.dumps({'prompt': workflow(name, prompt, mp, seed, steps)}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(URL + '/prompt', data=body,
                                                                headers={'Content-Type': 'application/json'})))
    pid = r['prompt_id']
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(f'{URL}/history/{pid}'))
        if pid in h:
            st = h[pid].get('status', {})
            if st.get('status_str') == 'error':
                raise RuntimeError(json.dumps(st)[:500])
            for node in h[pid]['outputs'].values():
                for im in node.get('images', []):
                    shutil.copy(os.path.join(COMFY, 'output', im.get('subfolder', ''), im['filename']), path_out)
                    return time.time() - t0
        time.sleep(2)
    raise TimeoutError(pid)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    s = edit(args[0], args[1], args[2] if len(args) > 2 else PROMPT, float(opts.get('mp') or 1.0), steps=int(opts.get('kroki') or 8))
    print(f'gotowe w {s:.0f} s')
