# Source-derived QA inventory

Static controls below come from `eesti/web/index.html`. Dynamic controls are owned by the screen modules in `eesti/web/js/`; case families are in `qa/test-plan.md`.

| Route | Element | ID | Label / destination |
|---|---|---|---|
| shell | a |  | Grove — на главную |
| shell | a |  | #course |
| shell | a |  | #path |
| shell | a |  | #course |
| shell | a |  | #review |
| shell | a |  | #exam |
| shell | button |  | read |
| shell | button |  | listen |
| shell | button |  | speak |
| shell | button |  | write |
| shell | details |  |  |
| shell | a |  | #path |
| shell | a |  | #course |
| shell | a |  | #review |
| shell | a |  | #exam |
| shell | a |  | #sonad |
| shell | a |  | #vihikud |
| shell | a |  | #status |
| shell | a | accountBtn | Profiil — профиль |
| shell | button | themeBtn |  |
| #path | button | practiceBtn |  |
| #path | a |  | #course |
| #path | a |  | #review |
| #path | a |  | #start |
| #course | button |  |  |
| #course | button |  |  |
| #course | button | freeLesson |  |
| #course | button | freeEdit |  |
| #course | select | freeTopic |  |
| #course | select | freeRule |  |
| #course | select | freeLevel |  |
| #course | button | freeBtn |  |
| #course | details | offline |  |
| #course | button | offlineGet |  |
| #course | button | offlinePractice |  |
| #course | button | offlineSend |  |
| #session | a |  | #course |
| #session | details |  |  |
| #session | select | wordTheme |  |
| #speak | select | speakMode | Harjutus — упражнение |
| #speak | select | speakTopic | Teema — тема |
| #speak | button | speakPlay |  |
| #speak | button | speakNext |  |
| #speak | button | recBtn |  |
| #speak | button | recSaveEval |  |
| #speak | details |  |  |
| #speak | details | evalSet |  |
| #speak | select | evalMode |  |
| #speak | button | evalNext |  |
| #speak | button | evalRec |  |
| #speak | textarea | evalTranscript |  |
| #speak | input | evalListened |  |
| #speak | input | evalPlanted |  |
| #speak | button | evalVerify |  |
| #speak | details | vestlus |  |
| #speak | button | vestlusStart |  |
| #speak | input | vestlusSay | Sinu vastus — твой ответ |
| #speak | button | vestlusMic |  |
| #speak | button | vestlusSend |  |
| #speak | a |  | https://sonaveeb.ee/pronunciation-exercises/ |
| #speak | a |  | https://sonaveeb.ee/learn |
| #status | button | remindBtn |  |
| #status | select | remindHour | Час напоминания |
| #status | a |  | /api/me/export |
| #write | textarea | text | Tekst — текст для проверки |
| #write | button | checkBtn |  |
| #write | details | queueBox |  |
| #write | button | queueSend |  |
| #exam | button |  |  |
| #exam | button |  |  |
| #exam | details | mock |  |
| #exam | button | mockWhole |  |
| #exam | a |  | #vihikud |
| #exam | details |  |  |
| #exam | details |  |  |
| #exam | details |  |  |
| #exam | button | checkpointBtn |  |
| #review | details |  |  |
| #review | button | loadReview |  |
| #review | a |  | #path |
| #review | a |  | #sonad |
| #review | a |  | #sonad |
| #review | a |  | #status |
| #sonad | button | workoutStart |  |
| #sonad | details |  |  |
| #sonad | select | vocLevel |  |
| #sonad | select | vocPos |  |
| #sonad | select | vocStatus |  |
| #sonad | button | vocBtn |  |
| #sonad | button | vocMoreBtn |  |
| #read | details |  |  |
| #read | select | readLevel |  |
| #read | button | loadLib |  |
| #read | button | libMoreBtn |  |
| #read | button | backToLib |  |
| #read | button | xlBtn |  |
| #read | button | quizBtn |  |
| #listen | button | dictPlay |  |
| #listen | button | dictNext |  |
| #listen | textarea | dictTyped | Etteütlus — что ты услышал |
| #listen | button | dictCheck |  |
| #listen | details |  |  |
| #listen | details |  |  |
| #listen | textarea | ttsText |  |
| #listen | select | voice |  |
| #listen | select | speed |  |
| #listen | button | speakBtn |  |
| #rule | details | sourceBox |  |

## API handlers

| Module | Verb | Route |
|---|---|---|
| assets.py | GET | / |
| assets.py | GET | /brand/{name} |
| assets.py | GET | /favicon.ico |
| assets.py | GET | /apple-touch-icon.png |
| assets.py | GET | /app.css |
| assets.py | GET | /js/{name} |
| assets.py | GET | /vendor/{name} |
| assets.py | GET | /fonts/{name} |
| assets.py | GET | /icon.svg |
| assets.py | GET | /icon.png |
| assets.py | GET | /sw.js |
| assets.py | GET | /manifest.webmanifest |
| exam.py | GET | /api/exam/{level} |
| exam.py | GET | /api/readiness/{level} |
| exam.py | GET | /api/milestones/{level} |
| exam.py | GET | /api/checkpoint/{level} |
| exam.py | POST | /api/checkpoint/{level}/result |
| exam.py | GET | /api/exam-spec/{level} |
| exam.py | GET | /api/goal |
| exam.py | POST | /api/goal |
| exam.py | GET | /api/goal.ics |
| exam.py | GET | /api/mock/{level}/{part} |
| exam.py | POST | /api/mock/{level}/{part} |
| exam.py | GET | /api/mock-run/{level} |
| exam.py | GET | /api/mock/{level} |
| exam.py | GET | /api/exam/file/{item_id} |
| exam.py | GET | /api/exam/pages/{item_id} |
| exam.py | GET | /api/exam/page/{item_id}/{page} |
| exam.py | GET | /api/exam/image/{item_id}/{page}/{index} |
| exam.py | GET | /api/exam/text/{item_id} |
| exam.py | GET | /api/exam/native/{item_id} |
| exam.py | POST | /api/exam/native/{item_id}/check |
| grammar.py | POST | /api/check |
| grammar.py | GET | /api/lookup/{word} |
| grammar.py | POST | /api/translate |
| grammar.py | GET | /api/enrich/{word} |
| grammar.py | POST | /api/tutor |
| health.py | GET | /api/health |
| health.py | GET | /api/status |
| health.py | GET | /api/engines |
| library.py | GET | /api/modes |
| library.py | GET | /api/library |
| library.py | GET | /api/reading/next |
| library.py | GET | /api/library/{item_id} |
| library.py | GET | /api/read/questions/{item_id} |
| library.py | POST | /api/read/questions/{item_id} |
| library.py | POST | /api/read/answer |
| notion.py | POST | /api/notion/queue |
| notion.py | GET | /api/notion/pending |
| notion.py | POST | /api/notion/push |
| practice.py | GET | /api/curriculum |
| practice.py | POST | /api/course/topics/{topic}/skip |
| practice.py | GET | /api/lesson/{topic} |
| practice.py | GET | /api/themes |
| practice.py | POST | /api/practice |
| practice.py | POST | /api/practice/answer |
| practice.py | GET | /api/plan |
| practice.py | GET | /api/testout/{topic} |
| practice.py | GET | /api/placement/next |
| practice.py | GET | /api/learning/sentences |
| practice.py | POST | /api/testout/{topic} |
| practice.py | GET | /api/pack |
| profile.py | GET | /api/auth/me |
| profile.py | GET | /api/me |
| profile.py | POST | /api/me |
| profile.py | POST | /api/me/onboarding |
| profile.py | POST | /api/me/reset |
| profile.py | POST | /api/me/restore |
| profile.py | POST | /api/guest/reset |
| review.py | GET | /api/review |
| review.py | POST | /api/review |
| review.py | POST | /api/review/grade |
| review.py | POST | /api/mine |
| review.py | GET | /api/review/stats |
| sources.py | GET | /api/sources |
| speech.py | POST | /api/speak |
| speech.py | GET | /api/speak |
| speech.py | GET | /api/speaking |
| speech.py | GET | /api/dictation/next |
| speech.py | POST | /api/dictation/answer |
| speech.py | GET | /api/asr |
| speech.py | GET | /api/asr/home |
| speech.py | POST | /api/transcribe |
| speech.py | POST | /api/transcribe/text |
| speech.py | GET | /api/speaking/readaloud |
| speech.py | POST | /api/speaking/feedback |
| speech.py | GET | /api/speaking/probe |
| speech.py | POST | /api/speaking/check |
| speech.py | GET | /api/speaking/check |
| speech.py | GET | /api/eval/available |
| speech.py | POST | /api/eval/clip |
| speech.py | POST | /api/eval/draft/{stem} |
| speech.py | POST | /api/eval/review/{stem} |
| speech.py | GET | /api/eval/prompt |
| speech.py | GET | /api/pronounce |
| state.py | POST | /api/progress/reset |
| state.py | POST | /api/state/remove-account |
| state.py | GET | /api/state/export |
| state.py | POST | /api/content/import |
| state.py | GET | /api/content/export |
| state.py | POST | /api/state/import |
| state.py | GET | /api/events |
| state.py | POST | /api/events/import |
| state.py | GET | /api/me/export |
| state.py | GET | /api/reminders |
| state.py | GET | /api/reminders/settings |
| state.py | POST | /api/reminders/settings |
| state.py | GET | /api/push/key |
| state.py | POST | /api/push/subscribe |
| state.py | POST | /api/push/unsubscribe |
| vocab.py | GET | /api/vocab |
| vocab.py | POST | /api/vocab/known |

## Frontend modules

- `eesti/web/js/chrome.js`
- `eesti/web/js/core.js`
- `eesti/web/js/exam.js`
- `eesti/web/js/icons.js`
- `eesti/web/js/lesson.js`
- `eesti/web/js/listen.js`
- `eesti/web/js/main.js`
- `eesti/web/js/media.js`
- `eesti/web/js/mock.js`
- `eesti/web/js/offline.js`
- `eesti/web/js/onboarding.js`
- `eesti/web/js/path.js`
- `eesti/web/js/profile.js`
- `eesti/web/js/reading.js`
- `eesti/web/js/remind.js`
- `eesti/web/js/review.js`
- `eesti/web/js/router.js`
- `eesti/web/js/sources.js`
- `eesti/web/js/speak.js`
- `eesti/web/js/state.js`
- `eesti/web/js/vocab.js`
- `eesti/web/js/voice.js`
- `eesti/web/js/words.js`
- `eesti/web/js/write.js`
