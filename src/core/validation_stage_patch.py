from .utils.async_compat import run_maybe_async


async def run_validators(entries, validators):
    out = []
    for e in entries:
        ok = True
        for v in validators:
            res = await run_maybe_async(v, e)
            if res is False:
                ok = False
                break
        if ok:
            out.append(e)
    return out
