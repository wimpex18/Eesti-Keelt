# -*- coding: utf-8 -*-
"""Desktop screens: Kordamine and Eksam, plus the foundations sheet."""
from gen_a import ic, desktop, artboard, CSS, FONTS

D2 = {}

# ── Järjekord ─────────────────────────────────────────────────────────
D2["review"] = desktop("review", "Järjekord", "Сюда попадают ошибки и слова из чтения. "
    "Интервалы считает FSRS: чем труднее даётся, тем чаще возвращается.", f"""
<div class="card">
  <div class="card-h"><h2>Kaart 4 / 12</h2><span class="ru">карточка</span>
    <div class="meter" style="width:200px"><i style="width:33%"></i></div>
    <span class="right">järgmine kordamine sõltub vastusest</span></div>
  <div class="flash">
    <div class="task" style="justify-content:center"><span class="form">omastav</span>
      <span class="lvl">A2</span><span class="gl">из ошибки 24.08</span></div>
    <div class="w" style="margin-top:14px">küsimus</div>
    <div class="actions" style="justify-content:center;margin-top:10px">
      <div class="iconbtn">{ic('vol')}</div></div>
    <div class="m">вопрос</div>
    <div class="hint" style="margin-top:14px;max-width:52ch;margin-left:auto;
      margin-right:auto">Mitu <b>küsimust</b> sa esitasid? — сколько вопросов ты задал?
      После числительного и слова <i>mitu</i> — osastav.</div>
    <div class="grades">
      <div class="grade g1">Uuesti<span>&lt; 1 min</span></div>
      <div class="grade">Raske<span>2 päeva</span></div>
      <div class="grade">Hea<span>6 päeva</span></div>
      <div class="grade g4">Lihtne<span>16 päeva</span></div>
    </div>
    <p class="hint" style="margin-top:12px">1 · 2 · 3 · 4 klaviatuurilt</p>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Rasked sõnad</h2><span class="ru">чаще всего ошибаешься</span>
    <span class="right">viimased 30 päeva</span></div>
  <div class="list">
    <div class="item"><div><div class="t">raamat → raamatu</div>
      <div class="m">obj-case · 4 viga 7 korrast</div></div>
      <div class="r"><div class="meter warn" style="width:110px"><i style="width:43%"></i></div>
        <span class="hint num">43%</span><div class="btn btn-sm">Harjuta</div></div></div>
    <div class="item"><div><div class="t">tulema — tulen / tulin / tulnud</div>
      <div class="m">ebareeglipärane verb · 3 viga 8 korrast</div></div>
      <div class="r"><div class="meter warn" style="width:110px"><i style="width:62%"></i></div>
        <span class="hint num">62%</span><div class="btn btn-sm">Harjuta</div></div></div>
    <div class="item"><div><div class="t">tervis → tervise</div>
      <div class="m">omastav · 2 viga 9 korrast</div></div>
      <div class="r"><div class="meter" style="width:110px"><i style="width:78%"></i></div>
        <span class="hint num">78%</span><div class="btn btn-sm">Harjuta</div></div></div>
  </div>
</div>
""", f"""
<div class="rcard"><h3>Järjekord täna</h3><div class="rbig">12 kaarti</div>
  <div class="rrow"><span>Tehtud</span><b>3</b></div>
  <div class="rrow"><span>Uued</span><b>4</b></div>
  <div class="rrow"><span>Kordused</span><b>5</b></div></div>
<div class="rcard"><h3>Kust need tulevad</h3>
  <div class="rrow"><span>Kirjutamise vead</span><b>6</b></div>
  <div class="rrow"><span>Lugemisest märgitud</span><b>4</b></div>
  <div class="rrow"><span>Harjutuste vead</span><b>2</b></div></div>
<div class="rcard"><h3>Homme</h3><div class="rbig">9</div>
  <p class="hint">Планирует FSRS. Пропущенный день не «сгорает» — карточки просто
    накапливаются.</p></div>
""", 1180)

# ── Töövihikud ────────────────────────────────────────────────────────
D2["vihikud"] = desktop("vihikud", "Töövihikud", "Официальные консультационные тетради "
    "HARNO, в том числе заполняемые на компьютере. Это домашняя работа, а не экзамен.", f"""
<div class="card">
  <div class="banner">{ic('info')}<span>Материалы <b>HARNO</b> здесь только
    проиндексированы: приложение хранит ссылку и описание, но не копию.
    Каждая тетрадь открывается на сайте экзаменационного центра.</span></div>
  <div class="pills" style="margin-top:18px">
    <div class="pill on">Kõik</div><div class="pill">A2</div>
    <div class="pill">B1</div><div class="pill">Arvutis täidetav</div></div>
  <div class="list" style="margin-top:16px">
    <div class="item ext">{ic('notebook')}
      <div><div class="t">A2 konsultatsiooni töövihik · lugemine ja kirjutamine</div>
        <div class="m">HARNO · PDF · 48 lk · arvutis täidetav</div></div>
      <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
    <div class="item ext">{ic('notebook')}
      <div><div class="t">A2 konsultatsiooni töövihik · kuulamine</div>
        <div class="m">HARNO · PDF + helifailid · 32 lk</div></div>
      <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
    <div class="item ext">{ic('notebook')}
      <div><div class="t">B1 konsultatsiooni töövihik · kõik osaoskused</div>
        <div class="m">HARNO · PDF · 74 lk · arvutis täidetav</div></div>
      <div class="r"><span class="lvl up">B1</span>{ic('ext')}</div></div>
    <div class="item ext">{ic('notebook')}
      <div><div class="t">B1 kirjutamise näidisülesanded ja hindamisjuhend</div>
        <div class="m">HARNO · PDF · 21 lk</div></div>
      <div class="r"><span class="lvl up">B1</span>{ic('ext')}</div></div>
  </div>
</div>
<p class="note">Пунктирная рамка означает одно: строка ведёт за пределы приложения.
  Ничего из этого не скачивается и не хранится здесь.</p>
""", f"""
<div class="rcard"><h3>Kust need on</h3>
  <div style="font-size:14px;font-weight:650">HARNO / EIS</div>
  <p class="hint">Haridus- ja Noorteamet — тот же орган, что проводит экзамен.
    Материалы бесплатны и лежат у них.</p>
  <a class="hint" style="color:var(--accent)">eis.ee {ic('ext')}</a></div>
<div class="rcard"><h3>Avatud</h3>
  <div class="rrow"><span>Töövihikuid</span><b>3 / 9</b></div>
  <div class="meter"><i style="width:33%"></i></div>
  <p class="hint">Засчитывается как «работа по чтению» в оценке готовности.</p></div>
""", 1000)

# ── Ülevaade ──────────────────────────────────────────────────────────
D2["exam"] = desktop("exam", "Ülevaade", "Четыре части, в каждой 25 баллов. Сдано, если "
    "в сумме ≥ 60 и ни одна часть не равна 0.", f"""
<div class="card">
  <div class="card-h">
    <div class="seg"><span class="on">A2</span><span>B1</span></div>
    <span class="right">Eksam pole broneeritud · планируется 2027</span></div>

  <div class="banner">{ic('alert')}<span><b>Это не прогноз.</b> Ниже — только то,
    что приложение измерило: сколько заданий сделано и с каким результатом.
    Реальный экзамен оценивают люди, и говорение (<b>rääkimine</b>) оценить
    здесь нельзя вообще.</span></div>

  <div style="margin-top:20px">
    <div class="part"><div class="mk yes">{ic('check')}</div>
      <div><div class="nm">Lugemine <i class="ru">чтение</i></div>
        <div class="ev">62 teksti loetud · keskmine tuttavus 74 %</div>
        <div class="nx">Достаточно материала пройдено для A2.</div></div>
      <div class="r"><div class="meter" style="width:120px"><i style="width:82%"></i></div>
        <div class="hint num" style="margin-top:6px">82 %</div></div></div>

    <div class="part"><div class="mk yes">{ic('check')}</div>
      <div><div class="nm">Kuulamine <i class="ru">аудирование</i></div>
        <div class="ev">41 etteütlust · keskmine 71 % sõnadest</div>
        <div class="nx">Стабильно выше порога последние три недели.</div></div>
      <div class="r"><div class="meter" style="width:120px"><i style="width:71%"></i></div>
        <div class="hint num" style="margin-top:6px">71 %</div></div></div>

    <div class="part"><div class="mk no">{ic('alert')}</div>
      <div><div class="nm">Kirjutamine <i class="ru">письмо</i></div>
        <div class="ev">14 teksti kontrollitud · 27 viga, neist 11 obj-case</div>
        <div class="nx">Слабое место — генитив против партитива у завершённого
          объекта. Это тема 11 на <b>Rada</b>.</div></div>
      <div class="r"><div class="meter warn" style="width:120px"><i style="width:54%"></i></div>
        <div class="hint num" style="margin-top:6px">54 %</div></div></div>

    <div class="part"><div class="mk unk">{ic('info')}</div>
      <div><div class="nm">Rääkimine <i class="ru">говорение</i></div>
        <div class="ev">Ei ole mõõdetav</div>
        <div class="nx">Приложение не оценивает произношение и речь — оно только
          озвучивает вопросы и даёт себя переслушать.</div></div>
      <div class="r"><span class="hint">—</span></div></div>
  </div>

  <div class="sep"></div>
  <div class="actions">
    <div class="btn btn-pri">Kontrolltöö<span class="ru">контрольная A2</span></div>
    <span class="hint">30 küsimust läbisegi kogu tasemest · ~20 min</span></div>
</div>

<div class="card">
  <div class="card-h"><h2>Ametlik materjal</h2><span class="ru">HARNO / EIS</span>
    <span class="right">viited, mitte koopiad</span></div>
  <div class="list">
    <div class="item ext">{ic('clip')}<div><div class="t">A2 näidiseksam 2025 · kõik osad</div>
      <div class="m">EIS · ülesanded ja helifailid</div></div>
      <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
    <div class="item ext">{ic('flag')}<div><div class="t">Hinnatud näidissooritused kommentaaridega</div>
      <div class="m">HARNO · kirjutamine ja rääkimine</div></div>
      <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
    <div class="item ext">{ic('play')}<div><div class="t">Sissejuhatav video: kuidas eksam käib</div>
      <div class="m">HARNO · 8 min</div></div>
      <div class="r"><span class="lvl">A2</span>{ic('ext')}</div></div>
  </div>
</div>
""", f"""
<div class="rcard"><h3>Lävend</h3><div class="rbig">≥ 60 / 100</div>
  <p class="hint">и ни одна из четырёх частей не равна нулю — иначе экзамен
    не сдан независимо от суммы.</p></div>
<div class="rcard"><h3>Osad</h3>
  <div class="rrow"><span>Lugemine</span><b>25 p</b></div>
  <div class="rrow"><span>Kuulamine</span><b>25 p</b></div>
  <div class="rrow"><span>Kirjutamine</span><b>25 p</b></div>
  <div class="rrow"><span>Rääkimine</span><b>25 p</b></div></div>
<div class="rcard"><h3>Eksami kuupäev</h3><div class="rbig">Valimata</div>
  <p class="hint">Дата не выбрана: сдача планируется на 2027 год.
    Обратного отсчёта здесь нет намеренно.</p></div>
""", 1400)

# ── Edenemine ─────────────────────────────────────────────────────────
BARS = [42,58,31,0,66,74,52,61,38,70,83,45,0,57]
bars = "".join('<i class="%s" style="height:%d%%"></i>'
               % ("off" if v == 0 else "", max(v, 4)) for v in BARS)

D2["status"] = desktop("status", "Edenemine", "Пять измерений, без общего балла: "
    "экзамен оценивает четыре части отдельно и заваливает за ноль в любой из них.", f"""
<div class="card">
  <div class="card-h"><h2>Kokkuvõte</h2><span class="ru">за 30 дней</span>
    <span class="right">seisuga 02.09.2026</span></div>
  <div class="tiles" style="grid-template-columns:repeat(4,minmax(0,1fr))">
    <div class="tile"><div class="k">Harjutusi</div><div class="v">612</div>
      <div class="n">78 % õigesti</div></div>
    <div class="tile"><div class="k">Tekste loetud</div><div class="v">62</div>
      <div class="n">14 800 sõna</div></div>
    <div class="tile"><div class="k">Sõnu teada</div><div class="v">1 480</div>
      <div class="n">+164 kuuga</div></div>
    <div class="tile"><div class="k">Rada</div><div class="v">11<span
      style="font-size:18px;color:var(--muted)"> / 26</span></div>
      <div class="n">42 % läbitud</div></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Harjutusi päevas</h2><span class="ru">последние 14 дней</span>
    <span class="right">keskmine 44 · 2 vahele jäänud päeva</span></div>
  <div class="bars">{bars}</div>
  <div class="axis"><span>20.08</span><span>27.08</span><span>02.09</span></div>
  <p class="hint" style="margin-top:10px">Пустой столбец — день без занятий.
    Здесь нет «серии»: пропуск ничего не обнуляет.</p>
</div>

<div class="card">
  <div class="card-h"><h2>Osaoskuste kaupa</h2><span class="ru">по видам речевой деятельности</span></div>
  <div style="display:flex;flex-direction:column;gap:16px">
    <div><div style="display:flex;justify-content:space-between;font-size:14px;
      font-weight:600"><span>Lugemine <i class="ru">чтение</i></span>
      <span class="num">82 %</span></div>
      <div class="meter" style="margin-top:8px"><i style="width:82%"></i></div>
      <div class="hint" style="margin-top:6px">62 teksti · keskmine tuttavus 74 %</div></div>
    <div><div style="display:flex;justify-content:space-between;font-size:14px;
      font-weight:600"><span>Kuulamine <i class="ru">аудирование</i></span>
      <span class="num">71 %</span></div>
      <div class="meter" style="margin-top:8px"><i style="width:71%"></i></div>
      <div class="hint" style="margin-top:6px">41 etteütlust · 18 saadet avatud</div></div>
    <div><div style="display:flex;justify-content:space-between;font-size:14px;
      font-weight:600"><span>Kirjutamine <i class="ru">письмо</i></span>
      <span class="num" style="color:var(--warn)">54 %</span></div>
      <div class="meter warn" style="margin-top:8px"><i style="width:54%"></i></div>
      <div class="hint" style="margin-top:6px">14 teksti · 27 viga, neist 11 obj-case</div></div>
    <div><div style="display:flex;justify-content:space-between;font-size:14px;
      font-weight:600"><span>Rääkimine <i class="ru">говорение</i></span>
      <span class="hint">ei ole mõõdetav</span></div>
      <div class="meter" style="margin-top:8px"><i style="width:0"></i></div>
      <div class="hint" style="margin-top:6px">Приложение не оценивает речь —
        это делает экзаменатор.</div></div>
  </div>
</div>

<div class="card">
  <div class="card-h"><h2>Vead teemade kaupa</h2><span class="ru">30 дней</span>
    <span class="right">27 viga kokku</span></div>
  <div class="list">
    <div class="item"><div style="min-width:150px"><div class="t">obj-case</div>
      <div class="m">omastav vs osastav</div></div>
      <div class="meter warn" style="flex:1"><i style="width:100%"></i></div>
      <span class="num" style="font-weight:650;width:28px;text-align:right">11</span></div>
    <div class="item"><div style="min-width:150px"><div class="t">käänded</div>
      <div class="m">sise- ja väliskohakäänded</div></div>
      <div class="meter" style="flex:1"><i style="width:64%"></i></div>
      <span class="num" style="font-weight:650;width:28px;text-align:right">7</span></div>
    <div class="item"><div style="min-width:150px"><div class="t">sõnajärg</div>
      <div class="m">verb teisel kohal</div></div>
      <div class="meter" style="flex:1"><i style="width:45%"></i></div>
      <span class="num" style="font-weight:650;width:28px;text-align:right">5</span></div>
    <div class="item"><div style="min-width:150px"><div class="t">verbivormid</div>
      <div class="m">ebareeglipärased</div></div>
      <div class="meter" style="flex:1"><i style="width:36%"></i></div>
      <span class="num" style="font-weight:650;width:28px;text-align:right">4</span></div>
  </div>
</div>
""", f"""
<div class="rcard"><h3>Miks pole ühte numbrit</h3>
  <p class="hint">Экзамен считает четыре части отдельно и заваливает за ноль
    в любой из них. Один общий процент прятал бы именно ту часть,
    из-за которой можно не сдать.</p></div>
<div class="rcard"><h3>Kuu võrdlus</h3>
  <div class="rrow"><span>Harjutusi</span><b>+18 %</b></div>
  <div class="rrow"><span>Täpsus</span><b>+4 pp</b></div>
  <div class="rrow"><span>Uusi sõnu</span><b>+164</b></div></div>
<div class="rcard"><h3>Andmed</h3>
  <p class="hint">Всё считается на устройстве и в базе за Access.
    Ничего не отправляется наружу и не публикуется.</p></div>
""", 1560)

# ── Foundations ───────────────────────────────────────────────────────
def sw(hexv, name, note):
    return (f'<div><div style="height:56px;border-radius:12px;background:{hexv};'
            f'border:1px solid var(--line)"></div>'
            f'<div style="font-size:12.5px;font-weight:650;margin-top:8px">{name}</div>'
            f'<div class="hint num">{hexv}</div>'
            f'<div class="hint" style="margin-top:2px">{note}</div></div>')

FOUND = f"""
<div style="width:1180px;background:var(--paper);padding:36px 40px;font-family:var(--f-ui)">
  <h1 style="font-size:28px;font-weight:650;letter-spacing:-.025em">Alused</h1>
  <p class="sub" style="font-size:13.5px;color:var(--muted);margin-top:6px;max-width:74ch">
    Основа редизайна: палитра приложения сохранена без изменений, добавлены только
    вторичная краска текста и две тихие поверхности. Шкала отступов кратна 4 px,
    все элементы управления — не ниже 44 px.</p>

  <div class="card" style="margin-top:24px">
    <div class="card-h"><h2>Värvid</h2><span class="ru">из app.css, без изменений</span></div>
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:14px">
      {sw('#faf9f6','paper','фон страницы')}
      {sw('#ffffff','card','карточка')}
      {sw('#1b1b19','ink','основной текст')}
      {sw('#4a4a45','ink-2','вторичный (новый)')}
      {sw('#6b6b66','muted','подписи')}
      {sw('#e3e3de','line','границы')}
      {sw('#1c6b52','accent','действие, «верно»')}
      {sw('#e6f2ec','accent-soft','фон акцента')}
      {sw('#9a5b00','warn','внимание')}
      {sw('#a32c2c','bad','ошибка')}
      {sw('#4c6382','gloss','значение слова')}
      {sw('#f4f3ee','tint','тихая поверхность (новая)')}
    </div>
    <p class="note" style="margin-top:16px"><b>Один акцент.</b> Зелёный значит
      «действие» и «верно». Оранжевый и красный зарезервированы за состоянием и
      никогда не используются как «ещё один цвет ряда».</p>
  </div>

  <div class="card">
    <div class="card-h"><h2>Kiri</h2><span class="ru">Manrope · Literata</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:28px">
      <div>
        <div class="hint">Manrope — интерфейс, латиница и кириллица</div>
        <div style="font-size:28px;font-weight:650;letter-spacing:-.022em;margin-top:8px">
          Sihitis · осмысление</div>
        <div style="font-size:20px;font-weight:650;margin-top:10px">Kordamine 22/650</div>
        <div style="font-size:15px;margin-top:10px">Основной текст 15/1.55 — Ma lugesin
          eile raamatu läbi.</div>
        <div style="font-size:12.5px;color:var(--muted);margin-top:8px">Подпись 12,5 —
          осторожно, это не прогноз</div>
        <div style="font-size:10.5px;font-weight:700;letter-spacing:.09em;
          text-transform:uppercase;color:var(--muted);margin-top:8px">Раздел 10,5</div>
      </div>
      <div>
        <div class="hint">Literata — тексты для чтения, крупные числа</div>
        <div style="font-family:var(--f-read);font-size:30px;font-weight:600;
          margin-top:8px;letter-spacing:-.015em">1 480 · 42 %</div>
        <div class="prose" style="margin-top:10px;font-size:17px">Sel aastal tuli talv
          Eestisse varem kui tavaliselt. Öösel oli juba miinuskraade.</div>
        <p class="hint" style="margin-top:10px">Кириллицу и õ ä ö ü ü покрывают оба
          шрифта; запасные — system-ui и Georgia с близкими метриками.</p>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Elemendid</h2><span class="ru">высоты и радиусы</span></div>
    <div class="actions" style="align-items:flex-end">
      <div><div class="hint" style="margin-bottom:7px">44 px · основное</div>
        <div class="btn btn-pri">Harjuta<span class="ru">тренировка</span></div></div>
      <div><div class="hint" style="margin-bottom:7px">44 px · обычное</div>
        <div class="btn">Järgmine</div></div>
      <div><div class="hint" style="margin-bottom:7px">36 px · в строке</div>
        <div class="btn btn-sm">Kordamisse</div></div>
      <div><div class="hint" style="margin-bottom:7px">44 px · поле</div>
        <div class="sel" style="width:190px"><span>A1–B1</span>{ic('chev')}</div></div>
      <div><div class="hint" style="margin-bottom:7px">42 px · сегменты</div>
        <div class="seg"><span class="on">A2</span><span>B1</span></div></div>
      <div><div class="hint" style="margin-bottom:7px">32 px · фильтр</div>
        <div class="pill on">kergem</div></div>
    </div>
    <div class="sep"></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">
      <div><div class="hint">Радиусы</div>
        <div style="display:flex;gap:8px;margin-top:8px">
          <div style="width:44px;height:44px;border:1px solid var(--line);
            border-radius:9px;background:var(--card)"></div>
          <div style="width:44px;height:44px;border:1px solid var(--line);
            border-radius:12px;background:var(--card)"></div>
          <div style="width:44px;height:44px;border:1px solid var(--line);
            border-radius:20px;background:var(--card)"></div></div>
        <div class="hint" style="margin-top:6px">9 · 12 · 20 px</div></div>
      <div><div class="hint">Шкала отступов</div>
        <div style="display:flex;align-items:flex-end;gap:6px;margin-top:8px">
          <div style="width:4px;height:4px;background:var(--accent)"></div>
          <div style="width:8px;height:8px;background:var(--accent)"></div>
          <div style="width:12px;height:12px;background:var(--accent)"></div>
          <div style="width:16px;height:16px;background:var(--accent)"></div>
          <div style="width:24px;height:24px;background:var(--accent)"></div>
          <div style="width:32px;height:32px;background:var(--accent)"></div></div>
        <div class="hint" style="margin-top:6px">4 · 8 · 12 · 16 · 24 · 32</div></div>
      <div><div class="hint">Полоса прогресса</div>
        <div class="meter" style="margin-top:12px"><i style="width:64%"></i></div>
        <div class="hint" style="margin-top:8px">8 px, скруглённые концы</div></div>
      <div><div class="hint">Кольцо</div>
        <div class="ring" style="--pct:42%;margin-top:8px"><b>42%</b></div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Keelereegel</h2><span class="ru">какой язык где</span></div>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:20px">
      <div class="note"><b>Эстонский</b> — названия разделов и кнопки
        (<i>Kirjutamine</i>, <i>Kuula</i>), грамматические термины
        (<i>osastav</i>, <i>omastav</i>, <i>täisminevik</i>) и весь учебный
        материал. Интерфейс сам по себе — это тоже контакт с языком.</div>
      <div class="note"><b>Русский</b> — всё, что объясняет, предупреждает или
        обосновывает. Оговорка, которую нельзя прочитать, не является оговоркой:
        предупреждение «это не прогноз» и объяснение ошибки написаны по-русски
        намеренно. Эстонский термин при этом сохраняется и поясняется один раз:
        <i>«Rääkimine (говорение) оценить нельзя»</i> — не транслитерацией,
        а настоящим переводом (<i>osastav</i> → основа партитива).</div>
    </div>
  </div>
</div>
"""
D2["found"] = FOUND
