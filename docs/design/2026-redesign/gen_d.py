# -*- coding: utf-8 -*-
"""The eleven mobile screens (390x844)."""
from gen_a import ic, mobile

M = {}

M["path"] = mobile("learn", "Rada", "Rada", "путь · тема 11 из 26", f"""
<div class="mcard">
  <div style="display:flex;gap:14px;align-items:center">
    <div class="ring" style="--pct:42%;width:58px;height:58px"><b
      style="font-size:13px">42%</b></div>
    <div style="min-width:0">
      <div style="font-size:10.5px;font-weight:700;letter-spacing:.08em;
        text-transform:uppercase;color:var(--muted)">Praegune teema · 11 / 26</div>
      <div style="font-size:16px;font-weight:650;letter-spacing:-.015em;
        margin-top:4px;line-height:1.3">Sihitis: lõpetatud tegevus → omastav</div>
    </div>
  </div>
  <div class="meter" style="margin-top:14px"><i style="width:42%"></i></div>
  <div class="btn btn-pri btn-wide" style="margin-top:14px">Harjuta<span
    class="ru">тренировка</span></div>
</div>

<div class="mcard">
  <div class="task"><span class="w">raamat</span><span class="form">omastav</span>
    <span class="gl">книга</span><span class="lvl">A2</span></div>
  <p class="prompt" style="font-size:18px;margin:12px 0">Ma lugesin eile
    <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> läbi.</p>
  <div class="inp ph"><span>Kirjuta õige vorm…</span></div>
  <div style="display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:10px">
    <div class="btn btn-pri">Kontrolli</div>
    <div class="btn btn-quiet">{ic('skip')}</div></div>
</div>

<div class="mcard" style="background:var(--paper);border-style:dashed;
  display:flex;align-items:center;gap:10px">
  <div style="min-width:0"><div style="font-size:13.5px;font-weight:650">Kogu rada</div>
    <div class="hint">26 теми по порядку</div></div>
  <div style="margin-left:auto;color:var(--muted)">{ic('chev')}</div>
</div>
""")

M["drill"] = mobile("learn", "Harjutused", "Harjutused", "тренировка · 4 из 10", f"""
<div class="mcard">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="field"><span class="lab">Reegel</span>
      <div class="sel"><span>lõpetatud</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Raskus</span>
      <div class="sel"><span>A1–B1</span>{ic('chev')}</div></div>
  </div>
  <div style="display:grid;grid-template-columns:96px 1fr;gap:10px;margin-top:10px">
    <div class="field"><span class="lab">Arv</span>
      <div class="inp"><span class="num">10</span></div></div>
    <div class="btn btn-pri" style="align-self:end">Alusta</div>
  </div>
</div>

<div class="mcard">
  <div style="display:flex;align-items:center;gap:10px">
    <span class="hint num">4 / 10</span>
    <div class="meter" style="flex:1"><i style="width:40%"></i></div>
    <span class="hint num">3 õiget</span></div>
  <div class="task" style="margin-top:14px"><span class="w">kohv</span>
    <span class="form">osastav</span><span class="gl">кофе</span><span class="lvl">A1</span></div>
  <p class="prompt" style="font-size:18px;margin:12px 0">Ma ei joo hommikul
    <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>.</p>
  <div class="inp"><span>kohvi</span></div>
  <div style="display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:10px">
    <div class="btn btn-pri">Kontrolli</div>
    <div class="btn btn-quiet">{ic('skip')}</div></div>
</div>

<div class="item" style="margin:0">
  <div style="width:24px;height:24px;border-radius:7px;background:var(--warn-soft);
    color:var(--warn);display:grid;place-items:center;flex:none">{ic('x')}</div>
  <div style="min-width:0"><div class="t">Ma ei näinud <del
    style="color:var(--bad)">film</del> <ins style="color:var(--good);
    text-decoration:none;font-weight:650">filmi</ins>.</div>
    <div class="m">eitus → osastav</div></div>
  <div class="r"><div class="btn btn-sm btn-quiet">{ic('plus')}</div></div>
</div>
""")

M["read"] = mobile("learn", "Lugemine", "Lugemine", "чтение · 78 % слов знакомы", f"""
<div style="display:flex;align-items:center;gap:10px">
  <div class="btn btn-sm btn-quiet">← Nimekirja</div>
  <span class="hint" style="margin-left:auto">ERR · 240 sõna</span></div>
<div>
  <h2 style="font-size:20px;font-weight:650;letter-spacing:-.02em;line-height:1.3">
    Miks talv tuleb varem?</h2>
  <div style="display:flex;gap:8px;align-items:center;margin-top:10px">
    <span class="lvl">kergem</span><span class="hint">78 % tuttavad</span>
    <div class="btn btn-sm" style="margin-left:auto">{ic('vol')}0,85×</div></div>
  <div class="meter" style="margin-top:10px"><i style="width:78%"></i></div>
</div>
<div class="prose" style="font-size:17px">
  Sel aastal tuli <u>talv</u> Eestisse varem kui tavaliselt. Juba oktoobri lõpus
  <mark>sadas</mark> mitmes maakonnas lund ja öösel oli miinuskraade.
  Ilmateenistuse sõnul ei ole see <u>haruldane</u>, aga viimased viis aastat on
  olnud soojemad.
</div>
""", sheet=f"""
<div class="m-sheet">
  <div style="display:flex;align-items:flex-start;gap:10px">
    <div style="min-width:0">
      <div style="font-family:var(--f-read);font-size:24px;font-weight:600;
        letter-spacing:-.01em">haruldane</div>
      <div class="hint">omadussõna · A2 · sagedus 3 210</div>
      <div style="font-size:14px;color:var(--gloss);font-weight:600;margin-top:4px">
        редкий, необычный</div>
    </div>
    <div class="iconbtn" style="margin-left:auto;flex:none">{ic('x')}</div>
  </div>
  <div style="display:flex;gap:14px;margin-top:10px" class="hint">
    <span>omastav <b style="color:var(--ink)">haruldase</b></span>
    <span>osastav <b style="color:var(--ink)">haruldast</b></span></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
    <div class="btn btn-pri">{ic('plus')}Kordamisse</div>
    <div class="btn">Tean seda</div></div>
</div>
""")

M["sonad"] = mobile("learn", "Sõnavara", "Sõnavara", "словарь · A2 · nimisõnad", f"""
<div class="mcard">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="field"><span class="lab">Tase</span>
      <div class="sel"><span>A2</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Sõnaliik</span>
      <div class="sel"><span>nimisõna</span>{ic('chev')}</div></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px">
    <div class="field"><span class="lab">Olek</span>
      <div class="sel"><span>kõik</span>{ic('chev')}</div></div>
    <div class="btn btn-pri" style="align-self:end">Näita</div></div>
</div>
<div class="hint num">1–24 / 486 · sagedasemad ees</div>
<div class="wgrid" style="grid-template-columns:1fr 1fr">
  <div class="word"><span class="w">aeg</span><span class="lvl">A2</span>
    <span class="g">время · aja</span></div>
  <div class="word"><span class="w">koht</span><span class="lvl">A2</span>
    <span class="g">место · koha</span></div>
  <div class="word"><span class="w">tervis</span><span class="lvl">A2</span>
    <span class="g">здоровье</span></div>
  <div class="word settled"><span class="w">raamat</span><span class="lvl">A2</span>
    <span class="g">книга · tean</span></div>
  <div class="word"><span class="w">küsimus</span><span class="lvl">A2</span>
    <span class="g">вопрос</span></div>
  <div class="word"><span class="w">otsus</span><span class="lvl">A2</span>
    <span class="g">решение</span></div>
</div>
<div class="btn btn-quiet btn-wide">Veel sõnu</div>
""")

M["listen"] = mobile("learn", "Kuulamine", "Kuulamine", "аудирование · lause 3 / 8", f"""
<div class="mcard">
  <div style="display:flex;align-items:center;gap:12px">
    <div style="width:44px;height:44px;border-radius:999px;background:var(--accent);
      color:#fff;display:grid;place-items:center;flex:none">{ic('play')}</div>
    <div style="flex:1;min-width:0">
      <div class="meter"><i style="width:38%"></i></div>
      <div class="hint num" style="margin-top:6px">0:07 / 0:19 · 0,85×</div></div>
    <div class="btn btn-sm btn-quiet">Järgmine</div>
  </div>
  <div class="ta filled" style="margin-top:14px;min-height:76px;font-size:15px">
    Bussijaam asub kesklinnas turu kõrval</div>
  <div style="display:grid;grid-template-columns:1fr auto;gap:10px;margin-top:10px">
    <div class="btn btn-pri">Kontrolli</div>
    <span class="hint num" style="align-self:center">6 / 8</span></div>
</div>
<div class="corr">
  <span class="tag">etteütlus</span>
  <p class="fix" style="font-size:15px">Bussijaam asub <ins>kesklinnas</ins>
    <span style="color:var(--warn);text-decoration:underline wavy">turu</span>
    kõrval <ins>uue</ins> maja juures.</p>
  <p class="why">Пропущено <b>uue</b>, услышано <b>turu</b> вместо <b>turg</b>.</p>
</div>
<div class="item" style="margin:0">{ic('head')}
  <div style="min-width:0"><div class="t">Selges keeles — nädala uudised</div>
    <div class="m">ERR · 6 min · aeglane kõne</div></div>
  <div class="r">{ic('play')}</div></div>
""")

M["speak"] = mobile("learn", "Rääkimine", "Rääkimine", "говорение · Töö ja igapäev", f"""
<div class="mcard">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="sel"><span>Vasta küsimusele</span>{ic('chev')}</div>
    <div class="sel"><span>Töö ja igapäev</span>{ic('chev')}</div></div>
  <div class="task" style="margin-top:14px"><span class="form">küsimus</span>
    <span class="lvl up">B1</span></div>
  <p class="prompt" style="font-size:19px;margin:10px 0 14px">Kirjeldage oma
    tavalist tööpäeva. Mis on selle juures kõige raskem?</p>
  <div class="btn btn-wide">{ic('vol')}Kuula ette<span class="ru">прослушать</span></div>
</div>
<div class="btn btn-pri btn-wide" style="height:52px;background:var(--bad);
  border-color:var(--bad);box-shadow:0 2px 0 #7f2222">{ic('dot')}Salvesta vastus</div>
<div class="banner">{ic('info')}<span>Запись уходит в Cloudflare только для
  распознавания и <b>нигде не сохраняется</b>. Остаётся один текст.</span></div>
<div class="corr">
  <p class="fix" style="margin-top:0;font-size:15px">Minu tööpäev algab kell
    kaheksa. Kõige raskem on <mark>hommikul ärkama</mark>.</p>
  <p class="why">Это не оценка произношения — только то, что услышал
    распознаватель. После «kõige raskem on» ждём <b>ärgata</b>.</p>
</div>
""")

M["write"] = mobile("learn", "Kirjutamine", "Kirjutamine", "письмо · 38 слов", f"""
<div class="ta filled" style="min-height:118px;font-size:15px">Ma lugesin eile
  raamatut läbi ja siis kirjutasin sõbrale kirja. Homme tahan ma minna
  raamatukokku.</div>
<div style="display:grid;grid-template-columns:1fr auto;gap:10px">
  <div class="btn btn-pri">Kontrolli<span class="ru">проверить</span></div>
  <span class="hint num" style="align-self:center">38 sõna</span></div>
<div class="corr objcase">
  <span class="tag warn">obj-case</span>
  <p class="fix" style="font-size:15px">Ma lugesin eile <del>raamatut</del>
    <ins>raamatu</ins> läbi.</p>
  <p class="why">Наречие <b>läbi</b> делает действие завершённым, поэтому объект
    в <b>omastav</b> — основа генитива: <b>raamatu</b>.</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
    <div class="btn btn-sm">{ic('plus')}Logisse</div>
    <div class="btn btn-sm btn-quiet">Harjuta</div></div>
</div>
<div class="item" style="margin:0">
  <div style="min-width:0"><div class="t">Vigade logi</div>
    <div class="m">3 kirjet ootab saatmist</div></div>
  <div class="r">{ic('chev')}</div></div>
""")

M["review"] = mobile("revise", "Järjekord", "Järjekord", "повторение · 4 из 12", f"""
<div class="mcard" style="padding:20px 17px">
  <div style="display:flex;align-items:center;gap:10px">
    <span class="hint num">4 / 12</span>
    <div class="meter" style="flex:1"><i style="width:33%"></i></div></div>
  <div class="flash" style="padding:22px 0 6px">
    <div class="task" style="justify-content:center"><span class="form">omastav</span>
      <span class="lvl">A2</span></div>
    <div class="w" style="font-size:40px;margin-top:12px">küsimus</div>
    <div class="actions" style="justify-content:center;margin-top:8px">
      <div class="iconbtn">{ic('vol')}</div></div>
    <div class="m" style="font-size:18px">вопрос</div>
    <p class="hint" style="margin-top:12px">Mitu <b>küsimust</b> sa esitasid? —
      после <i>mitu</i> стоит osastav.</p>
  </div>
  <div class="grades" style="margin-top:16px">
    <div class="grade g1" style="font-size:12.5px">Uuesti<span
      style="font-size:10px">&lt;1 min</span></div>
    <div class="grade" style="font-size:12.5px">Raske<span
      style="font-size:10px">2 p</span></div>
    <div class="grade" style="font-size:12.5px">Hea<span
      style="font-size:10px">6 p</span></div>
    <div class="grade g4" style="font-size:12.5px">Lihtne<span
      style="font-size:10px">16 p</span></div>
  </div>
</div>
<div class="item" style="margin:0">
  <div style="min-width:0"><div class="t">Rasked sõnad</div>
    <div class="m">3 sõna · obj-case ees</div></div>
  <div class="r">{ic('chev')}</div></div>
""")

M["vihikud"] = mobile("revise", "Töövihikud", "Töövihikud", "тетради HARNO · ссылки", f"""
<div class="banner">{ic('info')}<span>Здесь только ссылки: копий материалов
  <b>HARNO</b> приложение не хранит.</span></div>
<div class="pills"><div class="pill on">Kõik</div><div class="pill">A2</div>
  <div class="pill">B1</div><div class="pill">Arvutis</div></div>
<div class="list">
  <div class="item ext">{ic('notebook')}
    <div style="min-width:0"><div class="t">A2 töövihik · lugemine ja kirjutamine</div>
      <div class="m">PDF · 48 lk · arvutis täidetav</div></div>
    <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
  <div class="item ext">{ic('notebook')}
    <div style="min-width:0"><div class="t">A2 töövihik · kuulamine</div>
      <div class="m">PDF + helifailid · 32 lk</div></div>
    <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
  <div class="item ext">{ic('notebook')}
    <div style="min-width:0"><div class="t">B1 töövihik · kõik osaoskused</div>
      <div class="m">PDF · 74 lk</div></div>
    <div class="r"><span class="lvl up">B1</span>{ic('ext')}</div></div>
</div>
""")

M["exam"] = mobile("exam", "Ülevaade", "Ülevaade", "готовность · A2", f"""
<div style="display:flex;align-items:center;gap:10px">
  <div class="seg"><span class="on">A2</span><span>B1</span></div>
  <span class="hint" style="margin-left:auto;text-align:right">Kuupäev valimata<br>2027</span></div>
<div class="banner">{ic('alert')}<span><b>Это не прогноз.</b> Показано только
  измеренное: сколько сделано и с каким результатом.</span></div>
<div class="mcard" style="padding:6px 15px">
  <div class="part"><div class="mk yes">{ic('check')}</div>
    <div style="min-width:0"><div class="nm">Lugemine</div>
      <div class="ev">62 teksti · 74 % tuttavaid sõnu</div></div>
    <div class="r"><b class="num" style="font-size:14px">82 %</b></div></div>
  <div class="part"><div class="mk yes">{ic('check')}</div>
    <div style="min-width:0"><div class="nm">Kuulamine</div>
      <div class="ev">41 etteütlust · keskmine 71 %</div></div>
    <div class="r"><b class="num" style="font-size:14px">71 %</b></div></div>
  <div class="part"><div class="mk no">{ic('alert')}</div>
    <div style="min-width:0"><div class="nm">Kirjutamine</div>
      <div class="ev">27 viga, neist 11 obj-case</div>
      <div class="nx">Это тема 11 на <b>Rada</b>.</div></div>
    <div class="r"><b class="num" style="font-size:14px;color:var(--warn)">54 %</b></div></div>
  <div class="part"><div class="mk unk">{ic('info')}</div>
    <div style="min-width:0"><div class="nm">Rääkimine</div>
      <div class="ev">Ei ole mõõdetav — оценивает экзаменатор</div></div>
    <div class="r"><span class="hint">—</span></div></div>
</div>
<div class="btn btn-pri btn-wide">Kontrolltöö<span class="ru">контрольная · 30 küsimust</span></div>
""")

BARS = [42,58,31,0,66,74,52,61,38,70,83,45,0,57]
bars = "".join('<i class="%s" style="height:%d%%"></i>'
               % ("off" if v == 0 else "", max(v, 4)) for v in BARS)

M["status"] = mobile("exam", "Edenemine", "Edenemine", "прогресс · 30 дней", f"""
<div class="tiles" style="grid-template-columns:1fr 1fr">
  <div class="tile"><div class="k">Harjutusi</div><div class="v"
    style="font-size:26px">612</div><div class="n">78 % õigesti</div></div>
  <div class="tile"><div class="k">Tekste</div><div class="v"
    style="font-size:26px">62</div><div class="n">14 800 sõna</div></div>
  <div class="tile"><div class="k">Sõnu teada</div><div class="v"
    style="font-size:26px">1 480</div><div class="n">+164 kuuga</div></div>
  <div class="tile"><div class="k">Rada</div><div class="v"
    style="font-size:26px">11 / 26</div><div class="n">42 % läbitud</div></div>
</div>
<div class="mcard">
  <div style="display:flex;align-items:baseline"><b style="font-size:14px">Harjutusi
    päevas</b><span class="hint" style="margin-left:auto">14 päeva</span></div>
  <div class="bars" style="height:52px;margin-top:12px">{bars}</div>
  <div class="axis"><span>20.08</span><span>27.08</span><span>02.09</span></div>
</div>
<div class="mcard">
  <div style="display:flex;justify-content:space-between;font-size:13.5px;
    font-weight:600"><span>Lugemine</span><span class="num">82 %</span></div>
  <div class="meter" style="margin-top:7px"><i style="width:82%"></i></div>
  <div style="display:flex;justify-content:space-between;font-size:13.5px;
    font-weight:600;margin-top:12px"><span>Kuulamine</span><span class="num">71 %</span></div>
  <div class="meter" style="margin-top:7px"><i style="width:71%"></i></div>
  <div style="display:flex;justify-content:space-between;font-size:13.5px;
    font-weight:600;margin-top:12px"><span>Kirjutamine</span>
    <span class="num" style="color:var(--warn)">54 %</span></div>
  <div class="meter warn" style="margin-top:7px"><i style="width:54%"></i></div>
</div>
""")
