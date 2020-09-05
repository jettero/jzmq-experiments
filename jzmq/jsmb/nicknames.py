#!/usr/bin/env python
# coding: utf-8


class NicknamesMixin:
    def __new__(cls, *a, nicknames_debug=False, **kw):
        if hasattr(cls, "_nicknames"):
            if nicknames_debug:
                if not callable(nicknames_debug):
                    print(f"NicknamesMixin(cls={cls})")

            def scope_bind(real_name):
                def read_rn(self):
                    return getattr(self, real_name)

                def write_rn(self, value):
                    return setattr(self, real_name, value)

                return read_rn, write_rn

            for real_name in cls._nicknames:
                read_rn, write_rn = scope_bind(real_name)
                p = property(read_rn)
                p = p.setter(write_rn)
                iter_obj = cls._nicknames[real_name]
                if isinstance(iter_obj, str):
                    iter_obj = (iter_obj,)
                for nickname in iter_obj:
                    if nicknames_debug:
                        if callable(nicknames_debug):
                            nicknames_debug(real_name, nickname)
                        else:
                            print(f"  setting nickname {real_name} -> {nickname}")
                    setattr(cls, nickname, p)
            del cls._nicknames
        obj = super().__new__(cls)
        return obj
