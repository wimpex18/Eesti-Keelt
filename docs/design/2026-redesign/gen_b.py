# -*- coding: utf-8 -*-
"""The eleven desktop screens."""
from gen_a import ic, desktop

D = {}

# ── Rada ──────────────────────────────────────────────────────────────
D["path"] = desktop("path", "Rada", "Порядок правил: тема открывается, когда пройдены те, "
    "на которых она стоит. Выбор словарной темы на этот порядок не влияет.", f"""
<div class="card">
  <div style="display:flex;gap:20px;align-items:center">
    <div class="ring" style="--pct:42%"><b>42%</b></div>
    <div style="min-width:0;flex:1">
      <div style="font-size:11px;font-weight:700;letter-spacing:.09em;
        text-transform:uppercase;color:var(--muted)">Praegune teema · 11 / 26</div>
      <div style="font-size:19px;font-weight:650;letter-spacing:-.015em;margin-top:6px">
        Sihitis: lõpetatud tegevus → omastav</div>
      <div class="hint" style="margin-top:5px">объект завершённого действия — генитив,
        а не партитив. Слабое место №1.</div>
    </div>
    <div class="actions" style="flex:none">
      <div class="btn btn-pri two">Harjuta<span class="ru">тренировка</span></div>
      <div class="btn two">Kogu rada<span class="ru">все темы</span></div>
    </div>
  </div>
  <div class="meter" style="margin-top:20px"><i style="width:42%"></i></div>
  <div style="display:flex;justify-content:space-between;margin-top:8px" class="hint">
    <span>11 teemat läbitud</span><span class="num">15 veel</span></div>
</div>

<div class="card">
  <div class="card-h"><h2>Harjutus</h2><span class="ru">упражнение 3 / 10</span>
    <span class="right num">7 / 8 õigesti</span></div>
  <div class="drill">
    <div class="task"><span class="w">raamat</span><span class="form">omastav</span>
      <span class="gl">книга</span><span class="lvl">A2</span></div>
    <p class="prompt">Ma lugesin eile <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> läbi.</p>
    <div style="display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px">
      <div class="inp ph"><span>Kirjuta õige vorm…</span></div>
      <div class="btn btn-pri">Kontrolli</div>
      <div class="btn btn-quiet">{ic('skip')}Jäta vahele</div>
    </div>
    <p class="hint" style="margin-top:12px">Enter — kontrolli · Tab — järgmine</p>
  </div>
  <div class="corr objcase" style="margin-top:16px">
    <span class="tag warn">obj-case</span>
    <p class="fix"><del>raamatut</del> → <ins>raamatu</ins></p>
    <p class="why"><b>Действие завершено</b> — «прочитал до конца», поэтому объект
      стоит в <b>omastav</b> (основа генитива), а не в osastav.
      Партитив остался бы, если бы действие длилось: <i>lugesin raamatut</i>.</p>
    <p class="gl-line"><b>raamat</b> — книга · omastav <b>raamatu</b> · osastav raamatut</p>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Kogu rada</h2><span class="ru">все темы по порядку</span>
    <span class="right">26 teemat</span></div>
  <div class="list" style="margin:0 -10px">
    <div class="topic done"><span class="st">{ic('check')}läbitud</span>
      <span class="nm">Nimisõna mitmus</span>
      <span class="r"><span class="lvl">A1</span><span class="hint num">92%</span></span></div>
    <div class="topic done"><span class="st">{ic('check')}läbitud</span>
      <span class="nm">Omastav ja osastav ainsuses</span>
      <span class="r"><span class="lvl">A2</span><span class="hint num">88%</span></span></div>
    <div class="topic now"><span class="st">{ic('dot')}praegu</span>
      <span class="nm">Sihitis: lõpetatud tegevus → omastav</span>
      <span class="r"><span class="lvl">A2</span><div class="btn btn-sm">Harjuta</div></span></div>
    <div class="topic"><span class="st">{ic('play')}avatud</span>
      <span class="nm">Sihitis: eitus → osastav</span>
      <span class="r"><span class="lvl">A2</span><div class="btn btn-sm">Harjuta</div></span></div>
    <div class="topic ref"><span class="st">{ic('book')}teatmik</span>
      <span class="nm">Käänete tabel — 14 käänet</span>
      <span class="r"><span class="lvl">A2</span><span class="hint">lugemiseks</span></span></div>
    <div class="topic lock"><span class="st">{ic('lock')}suletud</span>
      <span class="nm">Täisminevik ja enneminevik</span>
      <span class="r"><span class="lvl up">B1</span><span class="hint">2 eeldust</span></span></div>
  </div>
  <p class="note" style="margin-top:14px">Тема открывается, когда пройдены те,
    на которых она стоит. <b>Sõnavara teema</b> выбирает слова, а не правило —
    это разные вещи.</p>
</div>
""", f"""
<div class="rcard"><h3>Täna</h3><div class="rbig">24 harjutust</div>
  <div class="rrow"><span>Õigesti</span><b>19 / 24</b></div>
  <div class="rrow"><span>Aeg</span><b>18 min</b></div></div>
<div class="rcard"><h3>Kordamine</h3>
  <div style="display:flex;align-items:baseline;gap:9px">
    <div class="rbig">12</div><span class="hint">kaarti ootab</span></div>
  <div class="btn btn-sm btn-wide">Alusta kordamist</div></div>
<div class="rcard"><h3>Nõrk koht</h3>
  <div style="font-size:14px;font-weight:650">obj-case</div>
  <p class="hint">генитив против партитива у завершённого объекта — 61 % верных
    за 30 дней.</p>
  <div class="meter warn"><i style="width:61%"></i></div></div>
<div class="rcard"><h3>Sõnavara</h3>
  <div class="rrow"><span>Tean</span><b>1 480</b></div>
  <div class="rrow"><span>Õpin</span><b>212</b></div>
  <div class="rrow"><span>A2 kaetud</span><b>74%</b></div></div>
""", 1240)

# ── Harjutused ────────────────────────────────────────────────────────
D["drill"] = desktop("drill", "Harjutused", "Свободная тренировка: выбери правило и "
    "количество. Здесь ничего не записывается — ни прогресс, ни очередь повторения.", f"""
<div class="card">
  <div class="filters" style="grid-template-columns:1.5fr 1fr .8fr auto">
    <div class="field"><span class="lab">Reegel <i>правило</i></span>
      <div class="sel"><span>lõpetatud → omastav</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Raskus <i>уровень</i></span>
      <div class="sel"><span>A1–B1</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Arv <i>количество</i></span>
      <div class="inp"><span class="num">10</span></div></div>
    <div class="btn btn-pri">Alusta<span class="ru">начать</span></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Küsimus 4 / 10</h2>
    <div class="meter" style="width:180px"><i style="width:40%"></i></div>
    <span class="right num">3 õiget · 0 viga</span></div>

  <div class="drill">
    <div class="task"><span class="w">kohv</span><span class="form">osastav</span>
      <span class="gl">кофе</span><span class="lvl">A1</span></div>
    <p class="prompt">Ma ei joo hommikul <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>.</p>
    <div style="display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px">
      <div class="inp"><span>kohvi</span></div>
      <div class="btn btn-pri">Kontrolli</div>
      <div class="btn btn-quiet">{ic('skip')}Jäta vahele</div>
    </div>
  </div>

  <div class="sep"></div>
  <div class="list">
    <div class="item"><div class="mk yes" style="width:26px;height:26px;border-radius:8px;
        display:grid;place-items:center;background:var(--accent-soft);color:var(--good)">{ic('check')}</div>
      <div><div class="t">Ta ostis <b style="color:var(--good)">auto</b>.</div>
        <div class="m">lõpetatud → omastav · auto</div></div>
      <div class="r"><span class="lvl">A1</span></div></div>
    <div class="item"><div class="mk no" style="width:26px;height:26px;border-radius:8px;
        display:grid;place-items:center;background:var(--warn-soft);color:var(--warn)">{ic('x')}</div>
      <div><div class="t">Ma ei näinud <del style="color:var(--bad)">film</del>
        <ins style="color:var(--good);text-decoration:none;font-weight:650">filmi</ins>.</div>
        <div class="m">eitus → osastav · film</div></div>
      <div class="r"><span class="lvl">A2</span>
        <div class="btn btn-sm">{ic('plus')}Kordamisse</div></div></div>
    <div class="item"><div class="mk yes" style="width:26px;height:26px;border-radius:8px;
        display:grid;place-items:center;background:var(--accent-soft);color:var(--good)">{ic('check')}</div>
      <div><div class="t">Ta luges <b style="color:var(--good)">raamatut</b> terve õhtu.</div>
        <div class="m">kestev → osastav · raamat</div></div>
      <div class="r"><span class="lvl">A2</span></div></div>
  </div>
</div>

<p class="note">Здесь ничего не записывается: ни прогресс по <b>Rada</b>,
  ни очередь повторения. Это песочница — правило выбираешь ты, а не приложение.</p>
""", f"""
<div class="rcard"><h3>Selles seerias</h3><div class="rbig">3 / 10</div>
  <div class="rrow"><span>Õigesti</span><b>3</b></div>
  <div class="rrow"><span>Vigu</span><b>0</b></div>
  <div class="rrow"><span>Vahele jäetud</span><b>1</b></div></div>
<div class="rcard"><h3>Reegel</h3>
  <div style="font-size:14px;font-weight:650">lõpetatud → omastav</div>
  <p class="hint">Завершённое действие: объект целиком «использован» —
    <i>ostis auto</i>, а не <i>ostis autot</i>.</p></div>
<div class="rcard"><h3>Sama reegel mujal</h3>
  <div class="rrow"><span>Rada · teema 11</span>{ic('arrow')}</div>
  <div class="rrow"><span>Kordamine · 4 kaarti</span>{ic('arrow')}</div></div>
""", 1120)

# ── Lugemine ──────────────────────────────────────────────────────────
D["read"] = desktop("read", "Lugemine", "349 текстов, отсортированных по тому, сколько слов "
    "в них ты уже знаешь. Подчёркнутое слово — нажми, чтобы открыть карточку.", f"""
<div style="display:grid;grid-template-columns:272px minmax(0,1fr);gap:20px;align-items:start">
  <div class="card" style="padding:16px 14px">
    <div class="field" style="margin-bottom:12px"><span class="lab">Valik <i>подборка</i></span>
      <div class="sel"><span>soovitatud sulle</span>{ic('chev')}</div></div>
    <p class="hint" style="margin-bottom:10px">80 teksti · 62–78 % sõnadest tuttavad</p>
    <div class="list">
      <div class="item" style="flex-direction:column;align-items:stretch;gap:7px;
           border-color:var(--accent);background:var(--accent-soft)">
        <div class="t">Miks talv tuleb varem?</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="lvl">kergem</span><span class="m">ERR · 240 sõna</span></div>
        <div class="meter"><i style="width:78%"></i></div>
        <div class="m">78 % sõnadest tuttavad</div></div>
      <div class="item" style="flex-direction:column;align-items:stretch;gap:7px">
        <div class="t">Uus bussiliin ühendab kaks linna</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="lvl">keskmine</span><span class="m">Selges keeles · 310 sõna</span></div>
        <div class="meter"><i style="width:71%"></i></div>
        <div class="m">71 % sõnadest tuttavad</div></div>
      <div class="item" style="flex-direction:column;align-items:stretch;gap:7px">
        <div class="t">Kuidas hoida raha talvel</div>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="lvl">keskmine</span><span class="m">ERR · 275 sõna</span></div>
        <div class="meter"><i style="width:66%"></i></div>
        <div class="m">66 % sõnadest tuttavad</div></div>
    </div>
    <div class="btn btn-wide btn-quiet" style="margin-top:12px">Veel tekste</div>
  </div>

  <div class="card">
    <div class="card-h">
      <div class="btn btn-sm btn-quiet">← Nimekirja</div>
      <span class="right">ERR · Lihtsad uudised · 12.08.2026</span></div>
    <h2 style="font-size:22px;font-weight:650;letter-spacing:-.02em;line-height:1.3">
      Miks talv tuleb varem?</h2>
    <div style="display:flex;gap:8px;align-items:center;margin-top:12px;flex-wrap:wrap">
      <span class="lvl">kergem</span><span class="hint">240 sõna · 78 % tuttavad</span>
      <div class="btn btn-sm" style="margin-left:auto">{ic('vol')}Kuula 0,85×</div></div>
    <div class="meter" style="margin-top:12px"><i style="width:78%"></i></div>
    <div class="prose" style="margin-top:20px">
      Sel aastal tuli <u>talv</u> Eestisse varem kui tavaliselt. Juba oktoobri
      lõpus <mark>sadas</mark> mitmes maakonnas lund ja öösel oli miinuskraade.
      Ilmateenistuse sõnul ei ole see <u>haruldane</u>, aga viimased viis aastat
      on olnud soojemad.<br><br>
      «Inimesed <mark>unustavad</mark> kiiresti, milline on tavaline talv,»
      ütles ilmateenistuse spetsialist. Ta <u>soovitab</u> autojuhtidel rehvid
      õigel ajal vahetada ja jalakäijatel valida kindlad talvejalatsid.
    </div>
    <div class="sep"></div>
    <div class="actions">
      <div class="btn btn-sm">Tõlgi valitud lause<span class="ru">перевести</span></div>
      <span class="hint">vali tekstist lause — выдели предложение</span></div>
  </div>
</div>
""", f"""
<div class="rcard" style="border-color:var(--accent)">
  <h3>Sõnakaart</h3>
  <div style="font-family:var(--f-read);font-size:24px;font-weight:600;
    letter-spacing:-.01em">haruldane</div>
  <div class="hint">omadussõna · A2 · sagedus 3 210</div>
  <div style="font-size:14px;color:var(--gloss);font-weight:600">редкий, необычный</div>
  <div class="rrow"><span>omastav</span><b>haruldase</b></div>
  <div class="rrow"><span>osastav</span><b>haruldast</b></div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px">
    <div class="btn btn-sm">{ic('plus')}Kordamisse</div>
    <div class="btn btn-sm btn-quiet">Tean seda</div></div>
  <a class="hint" style="color:var(--accent)">Sõnaveeb {ic('ext')}</a></div>
<div class="rcard"><h3>Selles tekstis</h3>
  <div class="rrow"><span>Uusi sõnu</span><b>18</b></div>
  <div class="rrow"><span>Märgitud raskeks</span><b>4</b></div>
  <div class="rrow"><span>Loetud täna</span><b>2 teksti</b></div></div>
<div class="rcard"><h3>Miks see järjekord</h3>
  <p class="hint">Тексты отсортированы по доле знакомых слов, а не по CEFR:
    уровень есть только у официальных материалов экзамена.</p></div>
""", 1180)

# ── Sõnavara ──────────────────────────────────────────────────────────
D["sonad"] = desktop("sonad", "Sõnavara", "Список слов по уровню и части речи, самые "
    "частотные сверху. «Tean seda sõna» — выучено; «Pole vaja» — убрать из упражнений совсем.", f"""
<div class="card">
  <div class="filters" style="grid-template-columns:1fr 1fr 1fr auto">
    <div class="field"><span class="lab">Tase <i>уровень</i></span>
      <div class="sel"><span>A2</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Sõnaliik <i>часть речи</i></span>
      <div class="sel"><span>nimisõna</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Olek <i>статус</i></span>
      <div class="sel"><span>kõik</span>{ic('chev')}</div></div>
    <div class="btn btn-pri">Näita<span class="ru">показать</span></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>A2 · nimisõnad</h2>
    <span class="right num">1–24 / 486 · sagedasemad ees</span></div>
  <div class="wgrid" style="grid-template-columns:repeat(3,minmax(0,1fr))">
    <div class="word"><span class="w">aeg</span><span class="lvl">A2</span>
      <span class="g">время · omastav aja</span></div>
    <div class="word"><span class="w">koht</span><span class="lvl">A2</span>
      <span class="g">место · omastav koha</span></div>
    <div class="word"><span class="w">tööpäev</span><span class="lvl">A2</span>
      <span class="g">рабочий день</span></div>
    <div class="word settled"><span class="w">raamat</span><span class="lvl">A2</span>
      <span class="g">книга · tean seda sõna</span></div>
    <div class="word"><span class="w">tervis</span><span class="lvl">A2</span>
      <span class="g">здоровье · omastav tervise</span></div>
    <div class="word"><span class="w">arve</span><span class="lvl">A2</span>
      <span class="g">счёт · omastav arve</span></div>
    <div class="word"><span class="w">küsimus</span><span class="lvl">A2</span>
      <span class="g">вопрос · omastav küsimuse</span></div>
    <div class="word settled"><span class="w">maja</span><span class="lvl">A2</span>
      <span class="g">дом · tean seda sõna</span></div>
    <div class="word"><span class="w">otsus</span><span class="lvl">A2</span>
      <span class="g">решение · omastav otsuse</span></div>
  </div>
  <div class="actions" style="margin-top:16px;justify-content:center">
    <div class="btn btn-quiet">Veel sõnu<span class="ru">ещё слова</span></div></div>
</div>
""", f"""
<div class="rcard" style="border-color:var(--accent)">
  <h3>Valitud sõna</h3>
  <div style="font-family:var(--f-read);font-size:26px;font-weight:600;
    letter-spacing:-.015em">küsimus</div>
  <div class="hint">nimisõna · A2 · sagedus 812</div>
  <div style="font-size:14px;color:var(--gloss);font-weight:600">вопрос</div>
  <div class="rrow"><span>omastav</span><b>küsimuse</b></div>
  <div class="rrow"><span>osastav</span><b>küsimust</b></div>
  <div class="rrow"><span>mitmuse osastav</span><b>küsimusi</b></div>
  <div class="btn btn-sm btn-wide">{ic('plus')}Kordamisse<span class="ru">в повторение</span></div>
  <div class="btn btn-sm btn-wide btn-quiet">Tean seda sõna</div>
  <div class="btn btn-sm btn-wide btn-quiet">Pole vaja</div></div>
<div class="rcard"><h3>Kaetus</h3>
  <div class="rrow"><span>A1</span><b>96%</b></div>
  <div class="meter"><i style="width:96%"></i></div>
  <div class="rrow"><span>A2</span><b>74%</b></div>
  <div class="meter"><i style="width:74%"></i></div>
  <div class="rrow"><span>B1</span><b>38%</b></div>
  <div class="meter"><i style="width:38%"></i></div></div>
""", 1080)

# ── Kuulamine ─────────────────────────────────────────────────────────
D["listen"] = desktop("listen", "Kuulamine", "Диктант оценивается по словам. Ниже — архив "
    "передач и озвучка любого текста: замедленная речь 0,7× удобна для тренировки.", f"""
<div class="card">
  <div class="card-h"><h2>Etteütlus</h2><span class="ru">диктант</span>
    <span class="right num">lause 3 / 8</span></div>
  <div class="actions">
    <div class="btn btn-pri">{ic('play')}Kuula<span class="ru">слушать</span></div>
    <div class="btn">Järgmine</div>
    <div class="btn btn-quiet">0,85×</div>
    <span class="hint">Прослушай и запиши услышанное.</span></div>
  <div style="display:flex;align-items:center;gap:12px;margin-top:16px;
      border:1px solid var(--line);border-radius:12px;padding:11px 14px;background:var(--paper)">
    <div style="width:34px;height:34px;border-radius:999px;background:var(--accent);
      color:#fff;display:grid;place-items:center;flex:none">{ic('play')}</div>
    <div class="meter" style="flex:1"><i style="width:38%"></i></div>
    <span class="hint num">0:07 / 0:19</span></div>
  <div class="ta filled" style="margin-top:16px;min-height:84px">Bussijaam
    asub kesklinnas turu kõrval</div>
  <div class="actions" style="margin-top:14px">
    <div class="btn btn-pri">Kontrolli</div>
    <span class="hint num">6 / 8 sõna õigesti</span></div>
  <div class="corr" style="margin-top:16px">
    <span class="tag">etteütlus</span>
    <p class="fix">Bussijaam asub <ins>kesklinnas</ins>
      <del style="text-decoration:none;color:var(--warn);border-bottom:2px wavy var(--warn)">turu</del>
      kõrval <ins>uue</ins> maja juures.</p>
    <p class="why">Пропущено <b>uue</b>, услышано <b>turu</b> вместо <b>turg</b> —
      оба слова стоят в omastav, и на слух они различаются только длиной гласного.</p>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Arhiiv</h2><span class="ru">передачи и радиокурсы</span>
    <span class="right">82 saadet</span></div>
  <div class="list">
    <div class="item">{ic('head')}<div><div class="t">Keelesaade — «Kuidas eestlased puhkavad»</div>
      <div class="m">ERR · 12 min · transkriptsioon olemas</div></div>
      <div class="r"><span class="lvl">keskmine</span>{ic('play')}</div></div>
    <div class="item">{ic('head')}<div><div class="t">Raadiokursus B1 · osa 14</div>
      <div class="m">Vikerraadio · 9 min</div></div>
      <div class="r"><span class="lvl up">B1</span>{ic('play')}</div></div>
    <div class="item">{ic('head')}<div><div class="t">Selges keeles — nädala uudised</div>
      <div class="m">ERR · 6 min · aeglane kõne</div></div>
      <div class="r"><span class="lvl">kergem</span>{ic('play')}</div></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Mis tahes tekst → heli</h2><span class="ru">озвучить свой текст</span></div>
  <div class="ta" style="min-height:76px">Вставь текст из учебника или статьи…</div>
  <div class="filters" style="grid-template-columns:1fr 1fr auto;margin-top:14px">
    <div class="field"><span class="lab">Hääl <i>голос</i></span>
      <div class="sel"><span>Eesti · naishääl</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Kiirus <i>скорость</i></span>
      <div class="sel"><span>0,7× (õppijale)</span>{ic('chev')}</div></div>
    <div class="btn btn-pri">Loe ette<span class="ru">озвучить</span></div>
  </div>
</div>
""", f"""
<div class="rcard"><h3>Etteütlus täna</h3><div class="rbig">6 / 8</div>
  <div class="rrow"><span>Sõnu õigesti</span><b>75%</b></div>
  <div class="meter"><i style="width:75%"></i></div></div>
<div class="rcard"><h3>Kuulamine kokku</h3>
  <div class="rrow"><span>Etteütlusi</span><b>41</b></div>
  <div class="rrow"><span>Saateid avatud</span><b>18</b></div>
  <div class="rrow"><span>Keskmine tulemus</span><b>71%</b></div></div>
<div class="rcard"><h3>Что здесь оценивается</h3>
  <p class="hint">Диктант сверяется по словам — это единственная часть
    аудирования, где приложение может сказать, что ты ошибся.
    Архив и озвучка — только материал.</p></div>
""", 1320)

# ── Rääkimine ─────────────────────────────────────────────────────────
D["speak"] = desktop("speak", "Rääkimine", "Экзамен B1 — парный: двое отвечают по очереди "
    "и говорят друг с другом. Приложение озвучивает вторую сторону и даёт себя переслушать.", f"""
<div class="card">
  <div class="filters" style="grid-template-columns:1fr 1fr auto auto">
    <div class="field"><span class="lab">Harjutus <i>упражнение</i></span>
      <div class="sel"><span>Vasta küsimusele</span>{ic('chev')}</div></div>
    <div class="field"><span class="lab">Teema <i>тема</i></span>
      <div class="sel"><span>Töö ja igapäev</span>{ic('chev')}</div></div>
    <div class="btn">{ic('vol')}Kuula ette</div>
    <div class="btn btn-quiet">Järgmine</div>
  </div>
  <div style="border:1px solid var(--line);border-radius:16px;background:var(--paper);
      padding:24px;margin-top:18px">
    <div class="task"><span class="form">küsimus</span><span class="lvl up">B1</span></div>
    <p class="prompt big" style="margin-bottom:0">Kirjeldage oma tavalist tööpäeva.
      Mis on selle juures kõige raskem?</p>
  </div>
  <div class="actions" style="margin-top:18px">
    <div class="btn btn-pri" style="background:var(--bad);border-color:var(--bad);
      box-shadow:0 2px 0 #7f2222">{ic('dot')}Salvesta vastus<span class="ru">записать</span></div>
    <span class="hint">Микрофону нужен HTTPS или localhost.</span></div>
  <div class="banner" style="margin-top:16px">{ic('info')}
    <span>Запись отправляется в Cloudflare для распознавания речи и
      <b>нигде не сохраняется</b> — ни здесь, ни там. Остаётся только текст.
      Локально (<b>cli serve</b> + whisper.cpp) запись не покидает компьютер.</span></div>
</div>

<div class="card">
  <div class="card-h"><h2>Mida masin kuulis</h2><span class="ru">распознанный текст</span>
    <span class="right">Whisper · Cloudflare</span></div>
  <div style="display:flex;align-items:center;gap:12px;border:1px solid var(--line);
      border-radius:12px;padding:11px 14px;background:var(--paper)">
    <div style="width:34px;height:34px;border-radius:999px;background:var(--tint);
      display:grid;place-items:center;flex:none">{ic('play')}</div>
    <div class="meter" style="flex:1"><i style="width:100%"></i></div>
    <span class="hint num">0:34</span></div>
  <div class="corr" style="margin-top:16px">
    <p class="fix" style="margin-top:0">Minu tööpäev algab kell kaheksa.
      Kõige raskem on <mark style="background:var(--warn-soft);border-radius:3px;
      padding:0 2px">hommikul ärkama</mark>.</p>
    <p class="why">Это <b>не оценка произношения</b>. Показано только то, что
      услышал распознаватель: расхождение может быть его ошибкой, а не твоей.
      Форма <b>ärkama</b> здесь спорна — после «kõige raskem on» ждём
      <b>ärgata</b> (da-infinitiiv).</p>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Hääldus ja väljendid</h2><span class="ru">упражнения EKI</span></div>
  <p class="note">Произношение здесь <b>не оценивается</b> — это исследовательская
    задача, а не функция. У EKI уже есть бесплатные упражнения, и ссылка на них
    честнее выдуманного балла.</p>
  <div class="actions" style="margin-top:14px">
    <div class="btn">Hääldusharjutused {ic('ext')}</div>
    <div class="btn">Väljendid A1–B1 {ic('ext')}</div></div>
</div>
""", f"""
<div class="rcard"><h3>Eksami osa</h3><div class="rbig">Rääkimine</div>
  <p class="hint">25 баллов из 100. Оценивает экзаменатор — приложение не ставит
    оценку и не хранит запись.</p></div>
<div class="rcard"><h3>Küsimusi teemas</h3>
  <div class="rrow"><span>Töö ja igapäev</span><b>24</b></div>
  <div class="rrow"><span>Läbitud</span><b>9</b></div>
  <div class="meter"><i style="width:37%"></i></div></div>
<div class="rcard"><h3>Salvestus</h3>
  <div class="rrow"><span>Salvestatud</span><b>0</b></div>
  <p class="hint">Ничего не сохраняется — ни здесь, ни на сервере.</p></div>
""", 1300)

# ── Kirjutamine ───────────────────────────────────────────────────────
D["write"] = desktop("write", "Kirjutamine", "Проверка объясняет исправление словами; "
    "решение о правильности принимает не модель, а разбор форм.", f"""
<div class="card">
  <div class="ta filled" style="min-height:150px">Ma lugesin eile raamatut läbi
    ja siis kirjutasin sõbrale kirja. Homme tahan ma minna raamatukokku, sest
    ma ei leidnud seda raamat mida otsisin.</div>
  <div class="actions" style="margin-top:14px">
    <div class="btn btn-pri">Kontrolli<span class="ru">проверить</span></div>
    <span class="hint">Ctrl + Enter</span>
    <span class="right hint" style="margin-left:auto">38 sõna</span></div>
</div>

<div class="card">
  <div class="card-h"><h2>Parandused</h2><span class="ru">2 исправления</span>
    <span class="right">provaider: Claude · offline-varu olemas</span></div>
  <div class="corr objcase">
    <span class="tag warn">obj-case</span>
    <p class="fix">Ma lugesin eile <del>raamatut</del> <ins>raamatu</ins> läbi.</p>
    <p class="why">Наречие <b>läbi</b> делает действие завершённым — «прочитал до
      конца». Завершённый объект стоит в <b>omastav</b> (основа генитива):
      <b>raamatu</b>. Без <i>läbi</i> партитив был бы верен.</p>
    <div class="actions" style="margin-top:12px">
      <div class="btn btn-sm">{ic('plus')}Vigade logisse</div>
      <div class="btn btn-sm btn-quiet">Harjuta seda reeglit</div></div>
  </div>
  <div class="corr" style="margin-top:14px">
    <span class="tag">kääne</span>
    <p class="fix">…ma ei leidnud seda <del>raamat</del> <ins>raamatut</ins>,
      mida otsisin.</p>
    <p class="why">После отрицания <b>ei leidnud</b> объект всегда в
      <b>osastav</b>. Запятая перед <b>mida</b> обязательна.</p>
    <div class="actions" style="margin-top:12px">
      <div class="btn btn-sm">{ic('plus')}Vigade logisse</div>
      <div class="btn btn-sm btn-quiet">Harjuta seda reeglit</div></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Vigade logi</h2><span class="ru">ожидает отправки</span>
    <span class="right num">3 kirjet</span></div>
  <div class="list">
    <div class="item"><div class="mk unk" style="width:20px;height:20px;border-radius:6px;
        border:1.5px solid var(--accent);background:var(--accent-soft);display:grid;
        place-items:center;color:var(--accent)">{ic('check')}</div>
      <div><div class="t">raamatut → raamatu</div><div class="m">obj-case · 02.09</div></div>
      <div class="r"><span class="lvl">A2</span></div></div>
    <div class="item"><div style="width:20px;height:20px;border-radius:6px;
        border:1.5px solid var(--line)"></div>
      <div><div class="t">film → filmi</div><div class="m">eitus · 31.08</div></div>
      <div class="r"><span class="lvl">A2</span></div></div>
  </div>
  <div class="actions" style="margin-top:14px">
    <div class="btn btn-pri">Saada valitud Notionisse</div>
    <span class="hint">отправляются только отмеченные строки</span></div>
</div>
""", f"""
<div class="rcard"><h3>Vead 30 päevaga</h3><div class="rbig">27</div>
  <div class="rrow"><span>obj-case</span><b>11</b></div>
  <div class="meter warn"><i style="width:41%"></i></div>
  <div class="rrow"><span>käänded</span><b>7</b></div>
  <div class="meter"><i style="width:26%"></i></div>
  <div class="rrow"><span>sõnajärg</span><b>5</b></div>
  <div class="meter"><i style="width:19%"></i></div></div>
<div class="rcard"><h3>Kes otsustab</h3>
  <p class="hint">Модель <b>объясняет</b> исправление словами. Что считается
    ошибкой — решает разбор форм, а не модель.</p></div>
<div class="rcard"><h3>Kirjutatud</h3>
  <div class="rrow"><span>Sel nädalal</span><b>4 teksti</b></div>
  <div class="rrow"><span>Keskmine pikkus</span><b>62 sõna</b></div></div>
""", 1320)
