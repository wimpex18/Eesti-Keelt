# -*- coding: utf-8 -*-
"""What the first pass missed: dark, the middle width, states, components."""
from gen_a import ic, sidebar, top, CSS
from gen_b import D
from gen_c import D2
from gen_d import M

D.update(D2)
E = {}

def dark_desk(html):
    return ('<style>body{background:#16171a}</style>'
            + html.replace('class="dsk"', 'class="dsk dark"', 1)
                  .replace("сейчас: светлая", "сейчас: тёмная"))

def dark_mob(html):
    return ('<style>body{background:#16171a}</style>'
            + html.replace('class="phone"', 'class="phone dark"', 1))

# Same content, the other theme — so a difference is a theme bug, not a redraw.
E["dark_desk"] = dark_desk(D["path"])
E["dark_mob"] = dark_mob(M["read"])

# ── The middle width: 834 px ──────────────────────────────────────────
E["tablet"] = f"""
<div class="dsk" style="min-height:860px;width:834px;
  grid-template-columns:76px minmax(0,1fr)">
  {sidebar("path").replace('class="side"', 'class="side mini"', 1)}
  <main class="main" style="padding:24px 24px 36px">
    {top("Rada", "Порядок правил: тема открывается, когда пройдены те, "
         "на которых она стоит.")}
    <div class="card">
      <div style="display:flex;gap:16px;align-items:center">
        <div class="ring" style="--pct:42%"><b>42%</b></div>
        <div style="min-width:0;flex:1">
          <div style="font-size:11px;font-weight:700;letter-spacing:.09em;
            text-transform:uppercase;color:var(--muted)">Praegune teema · 11 / 26</div>
          <div style="font-size:18px;font-weight:650;letter-spacing:-.015em;
            margin-top:5px">Sihitis: lõpetatud tegevus → omastav</div>
        </div>
        <div class="btn btn-pri two" style="flex:none">Harjuta<span
          class="ru">тренировка</span></div>
      </div>
      <div class="meter" style="margin-top:18px"><i style="width:42%"></i></div>
    </div>

    <div class="card">
      <div class="card-h"><h2>Harjutus</h2><span class="ru">упражнение 3 / 10</span>
        <span class="right num">7 / 8 õigesti</span></div>
      <div class="drill">
        <div class="task"><span class="w">raamat</span><span class="form">omastav</span>
          <span class="gl">книга</span><span class="lvl">A2</span></div>
        <p class="prompt">Ma lugesin eile <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> läbi.</p>
        <div style="display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:12px">
          <div class="inp ph"><span>Kirjuta õige vorm…</span></div>
          <div class="btn btn-pri">Kontrolli</div>
          <div class="btn btn-quiet">{ic('skip')}</div>
        </div>
      </div>
    </div>

    <!-- The rail's cards, folded into a row. Below 1080 there is no third
         column to give them, and hiding them entirely is what the current
         layout does. -->
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
      gap:12px;margin-top:18px">
      <div class="rcard"><h3>Täna</h3><div class="rbig">24</div>
        <div class="rrow"><span>Õigesti</span><b>19 / 24</b></div></div>
      <div class="rcard"><h3>Kordamine</h3><div class="rbig">12</div>
        <div class="rrow"><span>kaarti ootab</span>{ic('arrow')}</div></div>
      <div class="rcard"><h3>Nõrk koht</h3>
        <div style="font-size:14px;font-weight:650">obj-case</div>
        <div class="meter warn"><i style="width:61%"></i></div>
        <div class="rrow"><span>õigesti 30 päevaga</span><b>61%</b></div></div>
    </div>

    <p class="note" style="margin-top:18px">834 px — это не широкий телефон и не
      узкий десктоп. Боковая панель остаётся, но становится иконками; правая
      колонка складывается под контент, а не исчезает.</p>
  </main>
</div>
"""

# ── States ────────────────────────────────────────────────────────────
E["states"] = f"""
<div style="width:1180px;background:var(--paper);padding:36px 40px;
  font-family:var(--f-ui)">
  <h1 style="font-size:28px;font-weight:650;letter-spacing:-.025em">Seisundid</h1>
  <p style="font-size:13.5px;color:var(--muted);margin-top:6px;max-width:76ch">
    Экраны выше показывают приложение, когда всё получилось. Здесь — остальное:
    нажатие, фокус, пустота, загрузка и отказ. Тексты взяты из кода, а не
    придуманы: в <b>app.css</b> 11 мест с <b>.banner</b> и 6 с <b>.empty</b>,
    и ни одно из них не было нарисовано.</p>

  <div class="card" style="margin-top:24px">
    <div class="card-h"><h2>Nupud</h2><span class="ru">кнопки · 5 состояний</span></div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">
      <div><div class="hint" style="margin-bottom:8px">Tavaline</div>
        <div class="btn btn-pri btn-wide">Kontrolli</div></div>
      <div><div class="hint" style="margin-bottom:8px">Kursor peal</div>
        <div class="btn btn-pri btn-wide" style="filter:brightness(1.07)">Kontrolli</div></div>
      <div><div class="hint" style="margin-bottom:8px">Vajutatud</div>
        <div class="btn btn-pri btn-wide" style="transform:translateY(2px);
          box-shadow:0 0 0 var(--accent-deep)">Kontrolli</div></div>
      <div><div class="hint" style="margin-bottom:8px">Fookus</div>
        <div class="btn btn-pri btn-wide" style="outline:2px solid var(--accent);
          outline-offset:2px">Kontrolli</div></div>
      <div><div class="hint" style="margin-bottom:8px">Kinni</div>
        <div class="btn btn-pri btn-wide" style="opacity:.55;box-shadow:none">Kontrolli</div></div>
    </div>
    <div class="sep"></div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px">
      <div><div class="hint" style="margin-bottom:8px">Tavaline</div>
        <div class="btn btn-wide">Järgmine</div></div>
      <div><div class="hint" style="margin-bottom:8px">Kursor peal</div>
        <div class="btn btn-wide" style="border-color:var(--accent);
          background:var(--accent-soft);color:var(--accent)">Järgmine</div></div>
      <div><div class="hint" style="margin-bottom:8px">Ootab vastust</div>
        <div class="btn btn-wide" style="color:var(--muted)">
          <span style="width:14px;height:14px;border-radius:50%;border:2px solid var(--line);
            border-top-color:var(--accent);display:inline-block"></span>Kontrollin…</div></div>
      <div><div class="hint" style="margin-bottom:8px">Fookus</div>
        <div class="btn btn-wide" style="outline:2px solid var(--accent);
          outline-offset:2px">Järgmine</div></div>
      <div><div class="hint" style="margin-bottom:8px">Kinni</div>
        <div class="btn btn-wide" style="opacity:.5">Järgmine</div></div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Väljad</h2><span class="ru">поля ввода</span></div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">
      <div><div class="hint" style="margin-bottom:8px">Tühi</div>
        <div class="inp ph"><span>Kirjuta õige vorm…</span></div></div>
      <div><div class="hint" style="margin-bottom:8px">Täidetud</div>
        <div class="inp"><span>raamatu</span></div></div>
      <div><div class="hint" style="margin-bottom:8px">Fookus</div>
        <div class="inp" style="border-color:var(--accent);outline:2px solid var(--accent);
          outline-offset:2px"><span>raamatu</span></div></div>
      <div><div class="hint" style="margin-bottom:8px">Vale vastus</div>
        <div class="inp" style="border-color:var(--bad);color:var(--bad)">
          <span>raamatut</span></div>
        <div style="font-size:12.5px;color:var(--bad);margin-top:6px">
          Действие завершено — нужен omastav.</div></div>
    </div>
    <p class="note" style="margin-top:16px">Поле не краснеет, пока не нажата
      <b>Kontrolli</b>: подсветка во время набора сообщает об ошибке раньше,
      чем человек закончил мысль.</p>
  </div>

  <div class="card">
    <div class="card-h"><h2>Tühjad vaated</h2><span class="ru">пустые состояния · текст из кода</span></div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">
      <div class="drill" style="text-align:center;padding:26px 20px">
        <div style="color:var(--muted);display:flex;justify-content:center">{ic('check')}</div>
        <div style="font-size:14.5px;font-weight:650;margin-top:10px">Järjekord on tühi</div>
        <p class="hint" style="margin-top:6px">Сейчас повторять нечего. Порешай
          упражнения или почитай тексты.</p>
        <div class="btn btn-sm" style="margin-top:12px">Harjutused</div></div>
      <div class="drill" style="text-align:center;padding:26px 20px">
        <div style="color:var(--muted);display:flex;justify-content:center">{ic('book')}</div>
        <div style="font-size:14.5px;font-weight:650;margin-top:10px">Tekste pole</div>
        <p class="hint" style="margin-top:6px">Текстов нет. Запусти
          <b>harvest-reading</b>, чтобы наполнить библиотеку.</p></div>
      <div class="drill" style="text-align:center;padding:26px 20px">
        <div style="color:var(--good);display:flex;justify-content:center">{ic('check')}</div>
        <div style="font-size:14.5px;font-weight:650;margin-top:10px">Vigu ei leitud</div>
        <p class="hint" style="margin-top:6px">Всё верно — ошибок не найдено.</p></div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Laadimine</h2><span class="ru">загрузка</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div class="hint" style="margin-bottom:10px">Список — скелет строки,
          не «крутилка» на весь экран</div>
        <div class="item" style="align-items:flex-start">
          <div style="flex:1"><div style="height:13px;width:62%;border-radius:5px;
            background:var(--tint)"></div>
            <div style="height:11px;width:38%;border-radius:5px;background:var(--tint);
              margin-top:8px"></div></div></div>
        <div class="item" style="align-items:flex-start">
          <div style="flex:1"><div style="height:13px;width:48%;border-radius:5px;
            background:var(--tint)"></div>
            <div style="height:11px;width:30%;border-radius:5px;background:var(--tint);
              margin-top:8px"></div></div></div>
      </div>
      <div>
        <div class="hint" style="margin-bottom:10px">Одиночное действие</div>
        <div class="drill" style="display:flex;align-items:center;gap:12px">
          <span style="width:16px;height:16px;border-radius:50%;border:2px solid var(--line);
            border-top-color:var(--accent);display:inline-block;flex:none"></span>
          <span style="font-size:14px;color:var(--muted)">Загружаю…</span></div>
        <p class="note" style="margin-top:12px">Форма скелета повторяет форму
          результата, иначе страница прыгает в момент, когда данные приходят.</p>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Tõrked</h2><span class="ru">отказы · то, что человек может сделать</span></div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="banner">{ic('alert')}<span><b>Микрофон не открылся:</b>
        Permission denied. Разреши доступ в настройках браузера — или продолжай
        без записи: вопрос можно прослушать и ответить вслух.</span></div>
      <div class="banner">{ic('alert')}<span><b>Звук не пришёл:</b> network error.
        Диктант остаётся на месте — нажми <b>Kuula</b> ещё раз.</span></div>
      <div class="banner" style="background:var(--tint);border-color:var(--line);
        color:var(--ink-2)">{ic('info')}<span><b>Проверка работает офлайн.</b>
        Модель недоступна, поэтому объяснение короче обычного: формы разобраны
        кодом, прозы не будет. Что считается ошибкой — не изменилось.</span></div>
      <div class="banner" style="background:var(--tint);border-color:var(--line);
        color:var(--ink-2)">{ic('info')}<span><b>Нет сети.</b> Упражнения и
        проверка форм работают: они считаются на устройстве. Не откроются
        тексты, аудио и материалы HARNO.</span></div>
    </div>
    <p class="note" style="margin-top:16px">Каждое сообщение говорит, <b>что
      делать дальше</b>. Отказ без следующего шага — это тупик, а не
      информация.</p>
  </div>
</div>
"""

# ── Components not shown on the screens ───────────────────────────────
E["parts"] = f"""
<div style="width:1180px;background:var(--paper);padding:36px 40px;
  font-family:var(--f-ui)">
  <h1 style="font-size:28px;font-weight:650;letter-spacing:-.025em">Komponendid</h1>
  <p style="font-size:13.5px;color:var(--muted);margin-top:6px;max-width:76ch">
    Части, которые на экранах видны только в одном состоянии. Здесь — все.</p>

  <div class="card" style="margin-top:24px">
    <div class="card-h"><h2>Valikvastus</h2>
      <span class="ru">.choices — два предложения, одно верное</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div>
        <div class="hint" style="margin-bottom:10px">До ответа</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div class="choice" style="text-align:left;background:var(--paper);
            border:1px solid var(--line);border-radius:10px;padding:12px 14px;
            font-size:14.5px">Ma lugesin eile raamatu läbi.</div>
          <div class="choice" style="text-align:left;background:var(--paper);
            border:1px solid var(--line);border-radius:10px;padding:12px 14px;
            font-size:14.5px">Ma lugesin eile raamatut läbi.</div>
        </div>
      </div>
      <div>
        <div class="hint" style="margin-bottom:10px">После ответа — выбран неверный</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div style="text-align:left;background:var(--accent-soft);
            border:1px solid var(--accent);border-radius:10px;padding:12px 14px;
            font-size:14.5px;display:flex;gap:10px;align-items:center">
            <span style="color:var(--good);flex:none">{ic('check')}</span>
            Ma lugesin eile raamatu läbi.</div>
          <div style="text-align:left;background:var(--warn-soft);
            border:1px solid var(--warn);border-radius:10px;padding:12px 14px;
            font-size:14.5px;display:flex;gap:10px;align-items:center">
            <span style="color:var(--warn);flex:none">{ic('x')}</span>
            Ma lugesin eile raamatut läbi.</div>
        </div>
        <p class="hint" style="margin-top:10px">Верный вариант подсвечивается
          всегда — даже когда человек его и выбрал.</p>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Kaart</h2><span class="ru">карточка: до и после</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div class="drill" style="text-align:center;padding:28px 20px">
        <div class="task" style="justify-content:center"><span class="form">omastav</span>
          <span class="lvl">A2</span></div>
        <div style="font-family:var(--f-read);font-size:38px;font-weight:600;
          margin-top:14px">küsimus</div>
        <div class="btn btn-wide" style="margin-top:20px;max-width:260px;
          margin-left:auto;margin-right:auto">Näita vastust<span
          class="ru">показать · пробел</span></div>
      </div>
      <div class="drill" style="text-align:center;padding:28px 20px">
        <div class="task" style="justify-content:center"><span class="form">omastav</span>
          <span class="lvl">A2</span></div>
        <div style="font-family:var(--f-read);font-size:38px;font-weight:600;
          margin-top:14px">küsimus</div>
        <div style="font-size:18px;font-weight:600;color:var(--gloss);margin-top:8px">вопрос</div>
        <div class="grades" style="max-width:340px;margin:18px auto 0">
          <div class="grade g1">Uuesti<span>&lt;1 min</span></div>
          <div class="grade">Raske<span>2 p</span></div>
          <div class="grade">Hea<span>6 p</span></div>
          <div class="grade g4">Lihtne<span>16 p</span></div></div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Kontrolltöö</h2><span class="ru">контрольная — идёт и закончена</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div class="drill">
        <div style="display:flex;align-items:center;gap:12px">
          <span class="hint num">Küsimus 12 / 30</span>
          <div class="meter" style="flex:1"><i style="width:40%"></i></div>
          <span class="hint num">08:41</span></div>
        <p class="prompt" style="font-size:17px">Eile ma <span class="blank">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>
          poest leiva ja piima.</p>
        <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px">
          <div class="inp ph"><span>Kirjuta vorm…</span></div>
          <div class="btn btn-pri">Edasi</div></div>
        <p class="hint" style="margin-top:12px">Ответы не показываются до конца —
          это проверка, а не тренировка.</p>
      </div>
      <div class="drill">
        <div style="display:flex;align-items:baseline;gap:12px">
          <div style="font-family:var(--f-read);font-size:34px;font-weight:600">23<span
            style="font-size:20px;color:var(--muted)"> / 30</span></div>
          <span class="tag">A2 · kontrolltöö</span></div>
        <div class="meter" style="margin-top:12px"><i style="width:77%"></i></div>
        <div style="margin-top:14px;display:flex;flex-direction:column;gap:9px">
          <div class="rrow"><span>Sihitis · omastav / osastav</span><b>5 / 9</b></div>
          <div class="rrow"><span>Käänded</span><b>8 / 10</b></div>
          <div class="rrow"><span>Verbivormid</span><b>10 / 11</b></div></div>
        <div class="actions" style="margin-top:14px">
          <div class="btn btn-sm btn-pri">Vead kordamisse</div>
          <div class="btn btn-sm">Vaata vastuseid</div></div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Mängija ja sõnad tekstis</h2>
      <span class="ru">плеер и слова в тексте</span></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
      <div style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;gap:12px;border:1px solid var(--line);
          border-radius:12px;padding:11px 14px;background:var(--paper)">
          <div style="width:34px;height:34px;border-radius:999px;background:var(--accent);
            color:#fff;display:grid;place-items:center;flex:none">{ic('play')}</div>
          <div class="meter" style="flex:1"><i style="width:0"></i></div>
          <span class="hint num">0:19</span></div>
        <div style="display:flex;align-items:center;gap:12px;border:1px solid var(--line);
          border-radius:12px;padding:11px 14px;background:var(--paper)">
          <div style="width:34px;height:34px;border-radius:999px;background:var(--accent);
            color:#fff;display:grid;place-items:center;flex:none">{ic('dot')}</div>
          <div class="meter" style="flex:1"><i style="width:38%"></i></div>
          <span class="hint num">0:07 / 0:19</span></div>
        <div style="display:flex;align-items:center;gap:12px;border:1px solid var(--line);
          border-radius:12px;padding:11px 14px;background:var(--paper);opacity:.7">
          <span style="width:34px;height:34px;border-radius:50%;border:2px solid var(--line);
            border-top-color:var(--accent);flex:none;display:inline-block"></span>
          <span class="hint">Звук готовится…</span></div>
        <div class="hint">Покой · воспроизведение · подготовка</div>
      </div>
      <div>
        <div class="prose" style="font-size:16px">Sel aastal tuli <u>talv</u>
          Eestisse varem kui tavaliselt. Juba oktoobri lõpus <mark>sadas</mark>
          mitmes maakonnas lund, ja see ei ole
          <span style="border-bottom:2px solid var(--accent);color:var(--accent)">haruldane</span>.</div>
        <div style="display:flex;flex-direction:column;gap:6px;margin-top:14px"
          class="hint">
          <span><u>подчёркнуто точками</u> — слово можно открыть</span>
          <span><mark>подсвечено</mark> — отмечено как трудное</span>
          <span style="color:var(--accent)">сплошное подчёркивание — открыто сейчас</span>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-h"><h2>Raja seisundid</h2><span class="ru">пять состояний темы</span></div>
    <div class="list" style="margin:0 -10px">
      <div class="topic done"><span class="st">{ic('check')}läbitud</span>
        <span class="nm">Nimisõna mitmus</span>
        <span class="r"><span class="lvl">A1</span><span class="hint num">92%</span></span></div>
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
    <p class="note" style="margin-top:14px">Состояние несут <b>и</b> цвет,
      <b>и</b> значок, и слово. Различие, которое держится на одном оттенке,
      различимо не для всех.</p>
  </div>
</div>
"""
