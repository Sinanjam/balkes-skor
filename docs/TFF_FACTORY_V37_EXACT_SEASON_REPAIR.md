# TFF Factory v3.7 Exact Season Repair

v3.7 zincir değil, sadece yazılan sezonları işler. Mevcut data/seasons önce staging'e alınır; trigger'daki sezonlar tek tek üretilir; final manifest staging'deki tüm sezonlardan yeniden kurulur. Böylece repair run eski çalışan sezonları düşürmez.

Başlatma:

```fish
fish start_v37_repair.fish 2024-2025 2023-2024
```

Güncel büyük eksik onarım listesi:

```fish
fish start_v37_repair.fish \
  2024-2025 2023-2024 2022-2023 2021-2022 2020-2021 2019-2020 2018-2019 \
  2017-2018 2016-2017 2015-2016 2014-2015 2010-2011 \
  2006-2007 2005-2006 2004-2005 2003-2004 2002-2003 \
  2001-2002 2000-2001 1999-2000 1998-1999 \
  1997-1998 1996-1997 1995-1996 1994-1995 \
  1993-1994 1992-1993 1991-1992 1990-1991
```
