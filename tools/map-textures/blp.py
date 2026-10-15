# BLP2 textures with DXT5 compression and mipmaps, the format the client's own map tiles
# come in: a quarter of a 32-bit TGA's size, on disk and in video memory, and mipmapped, so a
# texture drawn smaller than its pixels doesn't shimmer. numpy only.
#
# usage (a check): python -P tools/map-textures/blp.py <image> [out.blp]
#   encodes the image, decodes it again with Pillow and prints how close it came (PSNR)
import struct
import numpy as np

HEADER = 1172                   # magic, type, encoding, alpha bits, alpha type, mips, size, 16 offsets, 16 sizes, palette


def _blocks(img):
    """img (h, w, c) -> (n, 16, c): its 4 x 4 blocks, row by row (edges repeated to a multiple of 4)"""
    h, w, c = img.shape
    H, W = (h + 3) // 4 * 4, (w + 3) // 4 * 4
    if (H, W) != (h, w):
        img = np.pad(img, ((0, H - h), (0, W - w), (0, 0)), mode="edge")
    return img.reshape(H // 4, 4, W // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)


def _alpha(a):
    """(n, 16) alpha 0-255 -> (n, 8) bytes: two end values and eight interpolated steps"""
    a = a.astype(np.float32)
    a0, a1 = a.max(1), a.min(1)
    k = np.arange(8, dtype=np.float32)
    # (code 0: a0, 1: a1, 2-7: a0 to a1 in sevenths)
    w = np.where(k == 0, 0, np.where(k == 1, 7, k - 1)) / 7
    pal = a0[:, None] * (1 - w) + a1[:, None] * w
    idx = np.abs(a[:, :, None] - pal[:, None, :]).argmin(2).astype(np.uint64)
    bits = np.zeros(len(a), np.uint64)
    for i in range(16):
        bits |= idx[:, i] << np.uint64(3 * i)
    out = np.zeros((len(a), 8), np.uint8)
    out[:, 0], out[:, 1] = a0.astype(np.uint8), a1.astype(np.uint8)
    for i in range(6):
        out[:, 2 + i] = ((bits >> np.uint64(8 * i)) & np.uint64(255)).astype(np.uint8)
    return out


def _565(rgb):
    r, g, b = (np.clip(np.round(rgb[:, i] * m / 255), 0, m).astype(np.uint16) for i, m in enumerate((31, 63, 31)))
    return (r << 11) | (g << 5) | b


def _rgb(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], 1).astype(np.float32)


def _color(rgb, a):
    """(n, 16, 3) colour (and alpha, so unseen pixels don't steer it) -> (n, 8) bytes: two 565 end colours and
    a 2-bit index a pixel. Ends: the block's bounding box along its own diagonal, inset a little, refined
    once by least squares"""
    rgb = rgb.astype(np.float32)
    seen = (a > 0)[..., None]
    count = seen.sum(1)
    mean = np.where(count > 0, (rgb * seen).sum(1) / np.maximum(count, 1), rgb.mean(1))
    rgb = np.where(seen | (count[:, None] == 0), rgb, mean[:, None, :])   # (unseen pixels: the seen ones' mean)
    hi, lo = rgb.max(1), rgb.min(1)
    # the diagonal: channels that fall as the widest one rises run the other way
    main = (hi - lo).argmax(1)
    d = rgb - rgb.mean(1, keepdims=True)
    ref = np.take_along_axis(d, main[:, None, None].repeat(16, 1), 2)[..., 0]
    flip = (d * ref[..., None]).sum(1) < 0
    e0, e1 = np.where(flip, lo, hi), np.where(flip, hi, lo)
    inset = (e0 - e1) / 16
    e0, e1 = e0 - inset, e1 + inset
    for _ in range(2):
        t = _fit(rgb, e0, e1)
        # least squares ends for the steps chosen (t: each pixel's place from e0 to e1)
        w0, w1 = 1 - t, t
        a00, a11, a01 = (w0 * w0).sum(1), (w1 * w1).sum(1), (w0 * w1).sum(1)
        det = a00 * a11 - a01 * a01
        ok = np.abs(det) > 1e-6
        b0, b1 = (w0[..., None] * rgb).sum(1), (w1[..., None] * rgb).sum(1)
        n0 = (a11[:, None] * b0 - a01[:, None] * b1) / np.where(ok, det, 1)[:, None]
        n1 = (a00[:, None] * b1 - a01[:, None] * b0) / np.where(ok, det, 1)[:, None]
        e0, e1 = np.where(ok[:, None], np.clip(n0, 0, 255), e0), np.where(ok[:, None], np.clip(n1, 0, 255), e1)
    c0, c1 = _565(e0), _565(e1)
    swap = c0 < c1                                       # (four-colour order: the first end the larger)
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = _rgb(c0), _rgb(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    idx = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(3).argmin(2).astype(np.uint32)
    idx[c0 == c1] = 0
    bits = np.zeros(len(rgb), np.uint32)
    for i in range(16):
        bits |= idx[:, i] << np.uint32(2 * i)
    out = np.zeros((len(rgb), 8), np.uint8)
    out[:, 0:2] = c0.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 2:4] = c1.astype("<u2").view(np.uint8).reshape(-1, 2)
    out[:, 4:8] = bits.astype("<u4").view(np.uint8).reshape(-1, 4)
    return out


def _fit(rgb, e0, e1):
    """each pixel's nearest of the four steps from e0 to e1, as a place 0..1"""
    steps = np.array([0, 1 / 3, 2 / 3, 1], np.float32)
    pal = e0[:, None, :] * (1 - steps[None, :, None]) + e1[:, None, :] * steps[None, :, None]
    k = ((rgb[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(3).argmin(2)
    return steps[k]


def dxt5(rgba):
    """(h, w, 4) uint8 -> DXT5 bytes"""
    b = _blocks(rgba)
    return np.concatenate([_alpha(b[..., 3]), _color(b[..., :3], b[..., 3])], 1).tobytes()


def mips(rgba):
    """the image and each half-size copy down to 1 x 1 (averaged with its alpha, so clear pixels don't darken edges)"""
    out = [rgba]
    f = rgba.astype(np.float32) / 255
    while f.shape[0] > 1 or f.shape[1] > 1:
        fy, fx = (2 if f.shape[0] > 1 else 1), (2 if f.shape[1] > 1 else 1)
        h, w = f.shape[0] // fy, f.shape[1] // fx
        a = f[..., 3:4]
        pre = np.concatenate([f[..., :3] * a, a], 2).reshape(h, fy, w, fx, 4).mean((1, 3))
        a = pre[..., 3:4]
        f = np.concatenate([np.where(a > 0, pre[..., :3] / np.maximum(a, 1e-6), 0), a], 2)
        out.append(np.clip(np.round(f * 255), 0, 255).astype(np.uint8))
    return out


def write(path, rgba):
    """a BLP2, DXT5, with every mip level: rgba (h, w, 4) uint8, sides powers of two"""
    h, w = rgba.shape[:2]
    levels = [dxt5(m) for m in mips(rgba)][:16]
    offsets, sizes, at = [], [], HEADER
    for data in levels:
        offsets.append(at)
        sizes.append(len(data))
        at += len(data)
    offsets += [0] * (16 - len(offsets))
    sizes += [0] * (16 - len(sizes))
    head = b"BLP2" + struct.pack("<I4B2I", 1, 2, 8, 7, 1, w, h) + struct.pack("<16I", *offsets) + struct.pack("<16I", *sizes)
    with open(path, "wb") as f:
        f.write(head + bytes(1024) + b"".join(levels))


if __name__ == "__main__":
    import sys, os, tempfile
    from PIL import Image
    src = np.asarray(Image.open(sys.argv[1]).convert("RGBA"))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tempfile.gettempdir(), "blp-check.blp")
    write(out, src)
    back = np.asarray(Image.open(out).convert("RGBA")).astype(np.float32)
    a = src[..., 3:4].astype(np.float32) / 255
    err = ((back[..., :3] - src[..., :3]) ** 2 * a).sum() / max(1, a.sum() * 3)
    aerr = ((back[..., 3] - src[..., 3]) ** 2).mean()
    print("%s: %d bytes; colour PSNR %.1f dB (where it shows), alpha PSNR %.1f dB" % (
        out, os.path.getsize(out), 10 * np.log10(255 ** 2 / max(err, 1e-9)), 10 * np.log10(255 ** 2 / max(aerr, 1e-9))))
