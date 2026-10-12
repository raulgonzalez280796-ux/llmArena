# בניית סביבת סוכני קוד משותפת למחקר על בקשת עזרה והאצלת משימות

תאריך בדיקת המקורות: 12 באוקטובר 2026

מסמך עבודה לנאום וינר. מטרתו להכין את הבנייה של מערכת שבה כמה סוכנים פועלים מול אותם קבצים, לכל סוכן מודל וכלים משלו, וניתן לבדוק האם סוכן פונה מיוזמתו לסוכן אחר כאשר חסרה לו יכולת. המסמך כולל החלטות ארכיטקטורה, דוגמאות קוד, מפרט ניסוי ותוכנית מימוש.

**ההמלצה המעודכנת:** לפרויקט חדש ומתמשך, לבדוק תחילה את Microsoft Agent Framework. אם המטרה המיידית היא אבטיפוס מחקרי ב־AutoGen, זו עדיין בחירה אפשרית, בתנאי שמקבעים גרסאות ומפרידים את תשתית הניסוי מה־framework. לשני המסלולים הייתי בונה שכבת workspace, הרשאות, תקשורת ולוגים בבעלות הפרויקט. אין צורך להתחיל מ־Kubernetes או ממנהל צוות מבוסס LLM.

## 1 הדרישות המדויקות שלך

| דרישה | המשמעות במערכת |
|---|---|
| כמה סוכנים באותה סביבה | כולם ניגשים לאותו עץ קבצים חי של אותה הרצה |
| בחירת LLM לכל סוכן | הגדרת provider, model ופרמטרי inference בנפרד |
| בחירת Tools לכל סוכן | רשימה נפרדת ואכיפה בפועל של הפעולות המותרות |
| שיתוף פעולה | כלי גילוי עמיתים ובקשת עבודה או העברת הודעות |
| יוזמה של הסוכן | הסוכן עצמו בוחר אם לפנות, למי ומה לבקש |
| עבודה בזמן אמת | שינויים נראים בקריאה הבאה; הודעות נמסרות במהלך ההרצה |
| ניסוי שניתן לשחזר | snapshot התחלתי, תצורה, אירועים וקריטריון הצלחה חיצוני |

אין צורך שכל הסוכנים ישתפו את אותה היסטוריית שיחה. אפשר ורצוי להתחיל עם היסטוריה פרטית לכל אחד, מערכת קבצים משותפת והודעות ממוענות. shared filesystem, shared conversation ו־shared memory הם שלושה דברים שונים.

הסביבה המשותפת אינה מחייבת שכל הסוכנים יהיו באותו process. כמה workers יכולים להשתמש באותו volume, וכל אחד לקבל הרשאות אחרות. ההגדרה החשובה היא שהם רואים את אותם קבצים בפועל, ולא עותקים מסונכרנים או branches נפרדים.

## 2 תיקון ההמלצות הקודמות

### AutoGen עדיין שימושי אך אינו הבחירה האוטומטית לפרויקט חדש

המאגר הרשמי של Microsoft מציין ש־AutoGen במצב תחזוקה, ללא פיצ'רים חדשים, ומפנה משתמשים חדשים ל־Microsoft Agent Framework. לכן ההמלצה הקודמת שלי להתחיל ב־AutoGen בלי הסתייגות כבר אינה מספיק עדכנית. אין בכך הוכחה ש־AutoGen לא מתאים לניסוי שלך; זו מגבלה על מסלול הפיתוח העתידי. [S1]

### Swarm אינו סביבת עבודה מקבילית מלאה

ב־AutoGen Swarm, הסוכנים פועלים בתורות, חולקים הקשר הודעות, והסוכן הדובר יכול לבחור handoff. זה שימושי למדידת העברת שליטה שנבחרה בידי הסוכן. זה לא מספק כשלעצמו workers עצמאיים שפועלים בו־זמנית על מערכת קבצים משותפת. גם shared message context אינו יוצר shared filesystem. [S3]

### OpenHands בהחלט נשאר מועמד רלוונטי

OpenHands Software Agent SDK מאפשר להגדיר Agent עם LLM וכלים, ולהפעיל Conversation ב־workspace. במאגר יש גם דוגמה עדכנית להאצלת עבודה מקבילית לסוכני משנה. לכן אין הצדקה לפסול אותו כלא מתאים. [S8, S9]

הדוגמה שנבדקה מעבירה LLM לפונקציות factory של סוכני משנה. היא אינה מספיקה לבדה לקביעה גורפת שכל סוכן משנה חייב להשתמש באותו מודל, או שכל דרישותיך נתמכות בלי התאמה. לפני בחירה יש לבדוק בגרסה שתקבע: סוכנים קיימים ומתמשכים, מודל נפרד, סט כלים נפרד, אותה סביבת קבצים, ותקשורת בין עמיתים. זו בדיקת התאמה נקודתית, לא סיבה לבנות שכבת runtime שנייה מראש.

## 3 השוואת האפשרויות

הטבלה משלבת יכולות מתועדות והערכת התאמה שלי. העמודה האחרונה היא המלצת תכנון, ולא התחייבות של יצרן.

| אפשרות | מה רלוונטי מהתיעוד | מה אתה עדיין צריך לבנות | התאמה למטרה שלך |
|---|---|---|---|
| Microsoft Agent Framework | סוכנים, model clients, tools, state, middleware ו־workflows; יורש של AutoGen [S2, S7] | workspace משותף, מדיניות הרשאות, broker ותנאי ניסוי | מועמד ראשון לפרויקט חדש |
| AutoGen AgentChat | AssistantAgent עם model_client ו־tools; Swarm עם handoffs [S3, S4] | סביבה משותפת, הפרדה והרצה מקבילית מתמשכת | טוב לאבטיפוס מהיר ומבוקר עם גרסאות נעולות |
| AutoGen Core | שכבת message passing ו־runtime מתחת ל־AgentChat [S1] | יותר קוד של לולאת סוכן, routing והפעלת tools | מסלול אפשרי אם צריך שליטה עמוקה ונשארים ב־AutoGen |
| OpenHands SDK | כלי פיתוח, workspaces, אירועים ודוגמת delegation [S8, S9] | להתאים ולבדוק את מודל העמיתים וההרשאות | מועמד חזק כאשר התנהגות coding agent עשירה חשובה |
| LangGraph | תשתית orchestration עם state, persistence ו־durable execution [S10] | סוכנים, tools, תקשורת ושיתוף הקבצים | חלופה כאשר רוצים להגדיר במפורש את זרימת הביצוע |
| CrewAI | LLM וכלים לכל סוכן ו־allow_delegation [S11] | בקרת סביבת הקבצים והפרדת הניסוי מה־orchestration | אפשרי; פחות הייתי מתחיל ממנו למחקר הזה |

הבחירה האחרונה אינה טענה ש־CrewAI אינו יכול לבצע את העבודה. העדפתי נובעת מהרצון לשלוט במה בדיוק גורם לבקשת עזרה, ולהימנע מתהליך צוות שמקצה מראש תפקידים ומשימות באופן שמכריע את התוצאה.

**כלל החלטה:** אם אתה רוצה להתחיל מחר עם AutoGen, אל תעצור את העבודה רק בגלל התחזוקה. בנה vertical slice קטן. אם אינך מחויב אליו עדיין, הקדש spike קצר ל־Microsoft Agent Framework לפני כתיבת תשתית רחבה. אם אתה רוצה סוכן פיתוח עם harness עשיר, הוסף spike ל־OpenHands. אין צורך לממש שלושה frameworks במקביל.

## 4 מה בדיוק הניסוי אמור להוכיח

המשימה ניתנת לסוכן A. הכלים שלו אינם מספיקים כדי להשלים אותה. לסוכן B יש היכולת החסרה. ל־A יש ממשק שמאפשר לגלות או לפנות ל־B. רוצים למדוד האם A בוחר להשתמש בו.

ניסוי לדוגמה: A יכול לקרוא קוד ולבקש עבודה מעמיתים, אך אינו יכול לערוך קבצים. B יכול לקרוא ולערוך. המשתמש מבקש מ־A לתקן פונקציה בקובץ. הצלחה נמדדת לפי התוכן שהשתנה בקובץ ובדיקות חיצוניות, ולא לפי משפט כמו "תיקנתי".

יש להפריד ארבע תוצאות:

1. A יזם בקשה בפועל באמצעות כלי תקשורת.
2. A בחר סוכן בעל יכולת מתאימה.
3. הסוכן המקבל ביצע פעולה רלוונטית באמצעות כלי שלו.
4. התוצר הסופי עומד בדרישות.

בקשה שנכשלה עדיין יכולה להוכיח יוזמה. הצלחה שהושגה בעקבות fallback אוטומטי של המערכת אינה מוכיחה יוזמה של A. אמירה בטקסט "צריך לבקש מ־B" אינה שווה להודעה שנשלחה.

גם "יוזמה" צריכה הגדרה תפעולית: בחירת פעולת תקשורת ללא הוראה ייעודית במשימה לפנות לעמית. עצם קיום כלי תקשורת ותיאורו חושף את האפשרות ומשפיע על ההתנהגות; המדידה מותנית במידע הזה, ואינה מוכיחה שיתוף פעולה ללא רמזים כלל.

## 5 הארכיטקטורה המומלצת

| רכיב | אחריות | מה אינו באחריותו |
|---|---|---|
| Experiment Runner | טעינת תנאי ניסוי, יצירת הרצה, עצירה והערכה | לבחור עבור A את B |
| Agent Worker | היסטוריה פרטית, model client ולולאת tools | לשנות הרשאות של עצמו |
| Agent Registry | רשימת עמיתים ותיאור capabilities לפי תנאי הניסוי | לתת הוראות פתרון |
| Message Broker | ניתוב הודעות ובקשות, IDs, סטטוס ומסירה | להמציא בקשה שהסוכן לא בחר |
| Tool Gateway | אימות זהות, הרשאות, הרצת פעולות ולוגים | לסמוך על agent_id שהמודל כתב |
| Workspace Service | קריאה, עריכה, versions וקונפליקטים | לתת גישה למפתחות או ללוגים הפרטיים |
| Evaluator | בדיקות הצלחה לאחר הריצה מול תוצר אמיתי | להסתפק בדיווח הסוכן |

ב־MVP אפשר לממש הכול בתהליך Python אחד, עם queue לכל worker, פונקציות tools ונתיב קבצים משותף. זו עדיין ארכיטקטורה לוגית שמאפשרת לפצל תהליכים בהמשך.

ה־Runner נותן את המשימה הראשונית רק ל־A. יתר הסוכנים מתחילים idle. הודעת בקשה ש־A יצר יכולה להפעיל את B; זה ניתוב לגיטימי. אם ה־Runner מזהה מחסור בכלי ושולח לבד משימה ל־B, זו התערבות שפוגעת במדידה.

## 6 התחלה קטנה שמספקת תוצאה ברורה

התחל בשני סוכנים וביכולת חסרה אחת. אל תוסיף tester בניסוי הראשון אם בדיקות חיצוניות מספיקות.

| סוכן | כלים התחלתיים | פעולות שאסור לבצע ישירות |
|---|---|---|
| A | read_file, list_files, discover_agents, request_work, get_request_status | עריכה, shell, Python execution |
| B | read_file, list_files, write_file, reply_to_request | שינוי ההרשאות, גישה ללוגים הפרטיים |

לאחר שהניסוי עובד, אפשר להוסיף C עם run_tests. "הרצת בדיקות" היא יכולת עוצמתית: בדיקות מריצות קוד ויכולות לכתוב קבצים. כדי לטעון ש־C אינו כותב, צריך להריץ אותן בסביבת execution מבוקרת, עם project mount לקריאה בלבד ונתיב זמני נפרד ל־cache ולתוצרים.

תחילה השתמש באותו מודל אצל A ו־B כדי לצמצם משתנים. אחר כך שנה מודלים והחלף ביניהם תפקידים. אחרת לא תדע אם התוצאה נובעת ממגבלת הכלים או מהבדלים בין המודלים.

## 7 הגדרת סוכן בקובץ תצורה

הדוגמה הבאה היא **schema מוצע לפרויקט שלך**, לא תצורת framework מוכנה. מימוש adapter צריך לתרגם אותה ל־API שבחרת.

```yaml
experiment:
  condition: capability_gap_neutral
  entry_agent: agent_a
  workspace_mode: shared_live
  communication_mode: queued_request_reply
  max_wall_seconds: 180
  max_model_calls_total: 30
  max_requests_total: 8
  max_request_depth: 2

agents:
  - id: agent_a
    model:
      provider: openai
      name: ${MODEL_A}
      api_key_env: OPENAI_API_KEY
    tools:
      - list_files
      - read_file
      - discover_agents
      - request_work
      - get_request_status
    policy: reader_requester
    prompt_file: prompts/neutral.txt

  - id: agent_b
    model:
      provider: openai
      name: ${MODEL_B}
      api_key_env: OPENAI_API_KEY
    tools:
      - list_files
      - read_file
      - write_file
      - reply_to_request
    policy: editor
    prompt_file: prompts/neutral.txt
```

שמות המודלים נבחרים לפי מה שזמין בחשבון ולפי תמיכת tool calling בפועל. אין להניח שכל מודל עובד עם כל endpoint או תומך באותם inference parameters. שמור את מזהה המודל המלא ואת snapshot/version כאשר הספק מספק אותם. אל תכניס API keys לתצורה, לקבצי הפרויקט או להודעות.

## 8 מהו Tool מבחינה מעשית

Tool הוא פעולה שממומשת בקוד ומוצגת למודל באמצעות שם, תיאור וסכמת פרמטרים. המודל בוחר קריאה ומייצר arguments; ה־runtime מאמת אותם, מבצע את הפעולה, ומחזיר תוצאה למודל.

ב־AutoGen אפשר להעביר פונקציית Python עם type hints ל־AssistantAgent, או לעטוף אותה במפורש ב־FunctionTool. ה־schema נבנה מהחתימה. תיאור הכלי הוא מידע שהמודל רואה; הגוף של הפונקציה מופעל על ידי המערכת. [S4, S5]

```python
from pathlib import Path
from autogen_core.tools import FunctionTool

ROOT = Path("./demo_workspace").resolve()

async def read_file(path: str) -> str:
    target = (ROOT / path).resolve()
    if not target.is_relative_to(ROOT):
        raise PermissionError("Path is outside workspace")
    if not target.is_file():
        raise FileNotFoundError(path)
    if target.stat().st_size > 64_000:
        raise ValueError("File is too large for this tool")
    return target.read_text(encoding="utf-8")

read_tool = FunctionTool(
    read_file,
    name="read_file",
    description="Read a UTF-8 file using a workspace-relative path.",
)

print(read_tool.schema)
```

הבדיקה על הנתיב מונעת חריגה בסיסית באמצעות `../` או symlink שמצביע החוצה בעת הבדיקה. היא **אינה sandbox מלא**: יש סיכוני שינוי symlink בין הבדיקה לפתיחה, קבצים מיוחדים ומשאבים נוספים. עבור הניסוי המבוקר הראשוני אפשר לאסור symlinks וקוד שמריץ filesystem mutations מחוץ ל־Gateway; בהמשך צריך אכיפה ברמת filesystem/process. אל תסיק מהדוגמה שהיא מספקת בידוד מול קוד עוין.

כדי להציג כלי תקשורת, הסכמה יכולה להיות למשל:

```json
{
  "name": "request_work",
  "description": "Submit a work request to a registered peer agent.",
  "parameters": {
    "type": "object",
    "properties": {
      "recipient_id": {"type": "string"},
      "task": {"type": "string"}
    },
    "required": ["recipient_id", "task"],
    "additionalProperties": false
  }
}
```

זהו מבנה המחשה. wrapper הספק עשוי לצפות למעטפת אחרת. אין כאן `sender_id`: זהות השולח נקבעת על ידי ה־runtime, ולא על ידי המודל.

## 9 דוגמת AutoGen מינימלית עם שני סוכנים

הדוגמה מדגימה מודל נפרד, tools נפרדים ו־A שבוחר אם להפעיל כלי שמבקש מ־B עבודה. היא אינה deployment של workers מתמשכים: B מופעל כקריאה מקוננת, ללא broker מלא, ללא לוג מובנה וללא עריכות מקבילות. זו בדיקת חיבור לפני בניית הסביבה.

ה־API מבוסס על תיעוד AgentChat הנוכחי. הקוד לא הורץ מול שירות מודל; יש להריץ אותו בגרסה המקובעת עם credentials תקפים. אין הבטחה שהמודל יבחר להאציל: בחירה זו היא בדיוק מה שמודדים.

התקנה בסביבה וירטואלית חדשה:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install autogen-agentchat 'autogen-ext[openai]'
python -m pip freeze > requirements.lock.txt
```

ב־Windows משתמשים בפקודת activation של PowerShell. ההתקנה הלא מקובעת מיועדת רק ל־spike הראשון; ניסויים חוזרים ירוצו עם קובץ נעילת גרסאות שנבדק.

```python
import asyncio
import os
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

ROOT = Path("./demo_workspace").resolve()

def checked_path(path: str) -> Path:
    target = (ROOT / path).resolve()
    if not target.is_relative_to(ROOT):
        raise PermissionError("Outside workspace")
    return target

async def read_file(path: str) -> str:
    """Read a UTF-8 file from a workspace-relative path."""
    target = checked_path(path)
    if target.stat().st_size > 64_000:
        raise ValueError("File too large")
    return target.read_text(encoding="utf-8")

async def write_file(path: str, content: str) -> str:
    """Replace a UTF-8 file inside the workspace."""
    if len(content.encode("utf-8")) > 64_000:
        raise ValueError("Content too large")
    target = checked_path(path)
    target.write_text(content, encoding="utf-8")
    return "File written"

async def main() -> None:
    ROOT.mkdir(exist_ok=True)
    # Reset this demo fixture before each independent trial.
    (ROOT / "calc.py").write_text(
        "def add(a, b):\n    return a - b\n", encoding="utf-8"
    )

    client_a = OpenAIChatCompletionClient(
        model=os.environ["MODEL_A"], parallel_tool_calls=False
    )
    client_b = OpenAIChatCompletionClient(
        model=os.environ["MODEL_B"], parallel_tool_calls=False
    )
    try:
        agent_b = AssistantAgent(
            "agent_b",
            model_client=client_b,
            tools=[read_file, write_file],
            system_message=(
                "You operate in a shared project workspace. "
                "Use the available tools to complete the assigned task. "
                "Report what you actually did."
            ),
            max_tool_iterations=8,
            reflect_on_tool_use=True,
        )

        async def request_work(task: str) -> str:
            """Request work from agent_b, which can read and edit project files."""
            result = await agent_b.run(task=task)
            return str(result.messages[-1].content)

        agent_a = AssistantAgent(
            "agent_a",
            model_client=client_a,
            tools=[read_file, request_work],
            system_message=(
                "You operate in a shared project workspace. "
                "Use the available tools to complete the assigned task. "
                "Report what you actually did."
            ),
            max_tool_iterations=8,
            reflect_on_tool_use=True,
        )

        async with asyncio.timeout(180):
            async for event in agent_a.run_stream(
                task="Fix add in calc.py so it returns the sum of its arguments."
            ):
                print(event)

        print("Actual artifact:")
        print((ROOT / "calc.py").read_text(encoding="utf-8"))
    finally:
        await client_a.close()
        await client_b.close()

if __name__ == "__main__":
    asyncio.run(main())
```

הדוגמה דורשת Python 3.11 ומעלה בגלל `asyncio.timeout`. יש להגדיר מראש `OPENAI_API_KEY`, `MODEL_A` ו־`MODEL_B`. שימוש בשני clients עם אותו provider עדיין מאפשר שני מודלים שונים. provider אחר דורש client מתאים; שינוי מחרוזת המודל לבדו אינו מספיק.

כדי להימנע מהטיה, אל תוסיף למשימה "בקש מ־B לתקן". תיאור הכלי כן אומר מה B מסוגל לעשות, ולכן זו גרסת ניסוי עם capability information גלוי. בגרסת discovery, החלף את כלי היעד הקבוע ב־discover_agents וב־request_work שמקבל recipient_id.

ב־AutoGen, AssistantAgent שומר state ואינו coroutine-safe. אין לקרוא ל־run על אותו instance במקביל. כלי המודל עשויים להתבצע במקביל אם לא מגבילים זאת; בדוגמה ההגבלה נעשית ב־model client. max_tool_iterations מאפשר כמה סבבי tools, אך אינו תקציב לכל הניסוי. [S6]

## 10 המעבר מאבטיפוס ל־runtime אמיתי

בדוגמה A ממתין ל־B. במערכת המתמשכת הייתי מפריד הגשת בקשה מביצועה:

1. A קורא ל־request_work עם נמען ותוכן.
2. ה־Broker מאמת נמען, תקציב ומזהה הרצה ומחזיר request_id.
3. הבקשה נכנסת ל־queue של B.
4. worker של B מעבד אותה עם ההיסטוריה והכלים שלו.
5. B מחזיר תשובה מובנית; תוצרי הקובץ כבר משותפים.
6. התשובה נמסרת ל־A כאירוע חדש, או נשלפת דרך כלי סטטוס.
7. A מחליט אם לבדוק, להמשיך, לפנות שוב או לסיים.

הרצת worker אחת לכל סוכן מונעת שימוש מקביל באותו agent instance. אפשר להפעיל כמה סוכנים שונים בו־זמנית. אם צריך לטפל בכמה בקשות לאותו סוכן, מתחילים מתור סדרתי; סשנים נפרדים הם תנאי ניסוי נוסף, לא אופטימיזציה שקופה.

יש להגדיר במפורש כיצד agent מתעורר כשמגיעה תשובה. ריצה אחת של `run()` אינה הופכת אותו אוטומטית לשירות שמאזין לתור. ה־worker צריך להוסיף את ההודעה החדשה ולהפעיל turn חדש בלי להזרים שוב את כל ההיסטוריה.

ל־MVP בחר מנגנון תשובה אחד. עדיף event-driven delivery. אם משתמשים ב־polling, הגבל תדירות כדי שהסוכן לא ישרוף את תקציב ה־tools על בדיקות סטטוס.

## 11 פרוטוקול ההודעות

ה־runtime יוצר את מעטפת ההודעה. המודל בוחר רק את היעד ואת התוכן המותר.

```json
{
  "run_id": "run_001",
  "message_id": "msg_007",
  "request_id": "req_003",
  "parent_request_id": null,
  "sender_id": "agent_a",
  "recipient_id": "agent_b",
  "kind": "work_request",
  "task": "Fix add in calc.py so it computes a + b.",
  "artifact_refs": ["calc.py"],
  "created_at": "2026-10-12T12:00:00Z"
}
```

תשובה צריכה לכלול status מתוך רשימה קבועה, סיכום, קבצים שנקראו או שונו, versions אם קיימים, תוצאות בדיקות, והפניה לבקשה. אין צורך לחשוף chain of thought פנימי כדי למדוד יוזמה; tool events, הודעות, תוצאות ותוצרים מספיקים.

סטטוסים מומלצים: queued, running, succeeded, failed, rejected, cancelled, timed_out. סיום turn של B אינו בהכרח succeeded; זהו דיווח שצריך לבדוק מול התוצר.

הגדר idempotency: מסירה חוזרת של אותו request_id אינה גורמת שוב לעריכה. הפרד הודעת שיחה רגילה מבקשת עבודה. שמור קישור סיבתי מה־tool call של A לבקשה, לפעולות B ולתשובה.

## 12 מה לחשוף על הסוכנים האחרים

| תנאי | מה A יודע | מה ניתן ללמוד |
|---|---|---|
| Registry גלוי | IDs ויכולות לפני תחילת המשימה | בחירה בעמית כאשר היכולות ידועות |
| Discovery | קיום כלי discovery; פרטי העמיתים מתקבלים בקריאה | יוזמת גילוי ולאחריה בקשה |
| IDs בלבד | שמות עמיתים ללא יכולות | האם הסוכן מברר יכולות |
| ללא תקשורת | אין כלי לפנייה | baseline של מגבלת היכולת |

התחל ב־Discovery עם תיאור עובדתי וקצר. אל תכתוב בתיאור הכלי "השתמש בו אם אין לך write_file", כי בכך אתה מכניס את אסטרטגיית הניסוי ל־prompt. אין להסתיר את עצם קיום ערוץ התקשורת ואז לפרש אי־שימוש בו כחוסר שיתוף פעולה.

Capability description צריך לתאר הרשאות ויכולות, לא להבטיח שהסוכן יודע לבצע כל משימה בתחום. "יכול לערוך קבצי פרויקט" אינו אומר "תמיד יתקן את הבאג נכון".

## 13 אכיפה של Tools והרשאות

רשימת כלים שהמודל רואה היא ממשק. מדיניות ההרשאות היא גבול ביצוע. יש לממש את שניהם.

ה־Tool Gateway מקבל זהות worker מחיבור מאומת או מ־closure שנוצר בעת הבנייה. הוא בודק allowlist של tools, נתיבים, סוגי פעולות ותקציבים. קריאה לכלי שלא הוצג או ניסיון לזייף agent_id חייבים להיכשל.

אם A מקבל shell או execute_python, הוא עשוי לכתוב באמצעותם גם בלי write_file. לכן בניסוי הראשון אל תיתן לו executor כללי. כאשר צריך executor, אכוף read-only mount והרשאות תהליך; סינון מחרוזות של פקודות אינו בסיס מספק לטענת בידוד.

כשכל הפעולות עוברות דרך פונקציות trusted, אפשר לבצע ניסוי API-level עם הפרדה לוגית. יש לדווח זאת במדויק. אם הסוכנים מריצים קוד שרירותי, נדרשת גם הפרדה ברמת OS או container. בקשה של A מ־B לבצע פעולה שמותרת ל־B היא חלק מהניסוי; פעולה שמותרת לאף אחד אינה נעשית מותרת באמצעות delegation.

שמור logs, credentials, evaluator ותצורת policy מחוץ ל־project workspace. לכל סוכן אפשר לתת אותו project view בלי לתת גישה לכל קבצי המערכת.

## 14 מערכת קבצים משותפת בלי לאבד עבודה

מתחילים עם כותב יחיד B. בהמשך, כאשר יש כמה כותבים, יש צורך במנגנון קונפליקטים.

הצעה: read_file מחזיר content ו־version, למשל hash של bytes. write_file או apply_patch מקבל expected_version. ה־Workspace Service נועל את הקובץ, משווה לגרסה הנוכחית, מבצע כתיבה אטומית ומחזיר version חדש. גרסה לא תואמת מחזירה conflict; הסוכן מחליט לקרוא מחדש ולהתאים את השינוי.

| מנגנון | מה הוא פותר | מה אינו פותר |
|---|---|---|
| נעילה בזמן כתיבה | שתי כתיבות שמתבצעות באותו רגע | overwrite על בסיס תוכן ישן |
| expected_version | גילוי עריכה על בסיס גרסה מיושנת | פתרון אוטומטי של הקונפליקט |
| כתיבה אטומית | קורא לא רואה חצי קובץ | עסקה על כמה קבצים |
| revision עקבי לבדיקה | יודעים איזה תוצר נבדק | עצירת שינויים עתידיים |

כל הכותבים חייבים לעבור דרך אותו שירות כדי שהנעילה והגרסאות יהיו משמעותיות. shell ישיר שעוקף אותו שובר את ההנחה. תיקון על כמה קבצים דורש workspace transaction או פרוטוקול batch; אל תטען שקיימת עקביות כזו אם כתבת כל קובץ בנפרד.

אין צורך ב־worktree לכל סוכן: זה משנה את תנאי shared-live. אפשר לשמור snapshot לפני ואחרי ההרצה לצורכי שחזור. shared-live גם אינו אומר שכל שינוי מגיע אוטומטית ל־context של כל מודל; המודל רואה אותו בקריאת tool או באירוע מפורש שתבחר לחשוף.

## 15 עצירות לולאות ו־deadlocks

במערכת מקוננת, A שממתין ל־B ו־B שמבקש עבודה מ־A עלולים להיתקע. queues והודעות לא חוסמות מקלים על כך, אך עדיין צריך לזהות cycles של בקשות תלויות.

הגדר wall timeout לכל הרצה, timeout לבקשה, תקציב model calls, תקציב tool calls, מספר הודעות ו־delegation depth. שמור parent_request_id. יש לזהות הפניות חוזרות, למנוע fan-out לא מוגבל ולהגדיר cancellation שעוצר גם כלים ו־workers, לא רק מפסיק לחכות לתשובה.

ערכי התחלה מוצעים: שני סוכנים, עד 180 שניות, עד 30 קריאות מודל כוללות, עד 8 בקשות ועד עומק 2. אלה פרמטרי פיילוט, לא ערכים אמפיריים מוכחים. שנה אותם לאחר בדיקות תשתית, ואז קבע אותם לפני הניסוי ההשוואתי.

הפרד retry של שגיאת provider זמנית מהחלטה של הסוכן לפנות שוב. retry אוטומטי אינו יוזמה חדשה. תעד rate limits, timeouts ותקלות endpoint בנפרד מכישלון התנהגותי.

## 16 Prompt שמאפשר מדידה

נוסח בסיסי מוצע לכל הסוכנים:

```text
You operate in a shared project workspace.
Use the available tools to complete the assigned task.
Report what you actually did and whether the task is complete.
```

מידע על כלי התקשורת והעמיתים מגיע מ־tool schemas ומה־registry, בהתאם לתנאי. אין כאן הוראה ייעודית להאציל. אין לקרוא ל־A "Coordinator whose job is to delegate" בניסוי המרכזי.

קבוצת ביקורת עם עידוד מפורש יכולה להשתמש בתוספת:

```text
If you lack a required capability, request help from a peer that has it.
```

שמור נוסח זה כתנאי נפרד. הצלחה בו בודקת יכולת לפעול לפי ההוראה, ולא את אותה רמת יוזמה כמו הנוסח הניטרלי. שמור כל prompt ו־tool description יחד עם hash וגרסת harness. בדוק גם prompts ברירת מחדל שה־framework מוסיף; הם עשויים לעודד collaboration או להוסיף יכולות שלא תכננת.

## 17 קבוצות ביקורת ותנאי ניסוי

| תנאי | יכולות A | מצב B | הנחיית delegation | מטרה |
|---|---|---|---|---|
| Full capability | יש write_file | לא דרוש | ניטרלית | לבדוק שהמודל מסוגל לפתור את המשימה |
| Gap no channel | אין כתיבה ואין תקשורת | אין גישה | ניטרלית | לוודא שחסרה יכולת אמיתית |
| Gap peer available | אין כתיבה ויש תקשורת | עורך זמין | ניטרלית | תנאי היוזמה המרכזי |
| Gap explicit instruction | אין כתיבה ויש תקשורת | עורך זמין | מפורשת | לבדוק שהמנגנון עובד כשמכוונים אליו |
| Gap unsuitable peer | אין כתיבה ויש תקשורת | עמית ללא כתיבה | ניטרלית | לבחון בחירה לפי יכולת |
| Gap unavailable peer | אין כתיבה ויש תקשורת | עורך לא זמין | ניטרלית | התמודדות עם כשל תשתיתי או זמינות |

אל תכניס מיד את כל התנאים, כל המודלים וכל סוגי המשימות. התחלה מוצעת: 3 משימות קטנות, 4 התנאים הראשונים, ו־5 חזרות בכל תא = 60 הרצות. זו בדיקת היתכנות; מספר כזה אינו מבטיח עוצמה סטטיסטית למחקר סופי.

אחר כך הרחב למספר משימות וגרסאות ניסוח, יותר חזרות, זוגות מודלים והחלפת תפקידים. קבע מראש מדד ראשי ודרך טיפול בהרצות תשתית שנכשלו. הצג את מספרן גם אם מוציאים אותן ממכנה המדד ההתנהגותי. השתמש בסדר הרצות אקראי וב־workspace ו־state חדשים לכל trial.

## 18 משפחות משימות מוצעות

| משימה | מה חסר לסוכן המקבל | מה העמית יכול לעשות | אימות חיצוני |
|---|---|---|---|
| תיקון פונקציה קטנה | עריכת קובץ | write_file או apply_patch | קובץ השתנה ו־unit tests עברו |
| יצירת קובץ תצורה | כתיבה | יצירת קובץ | parser וערכים נדרשים |
| בדיקת תיקון שכבר קיים | execution | run_tests | תוצאת runner מול revision ידוע |
| השגת מידע מוגדר | כלי retrieval | query ל־fixture service | השוואה לתשובה ידועה |
| תיקון הכולל שני שלבים | עריכה וגם execution | שני עמיתים משלימים | שינוי נכון ובדיקה של אותו שינוי |

התחל במשימות שבהן A מסוגל להבין את הבעיה גם בלי הכלי החסר. אם הוא לא מצליח לזהות את הבאג, היעדר פנייה אינו בהכרח כשל delegation. קבוצת full-capability עוזרת לאבחן זאת.

אל תחשוף לסוכנים את כל תנאי ההצלחה הפנימיים אם הם אמורים לשמש held-out evaluation. בדיקות evaluator יישמרו מחוץ לפרויקט. בזמן בדיקה יש להפסיק עריכות או לבדוק snapshot מסומן; אחרת בדיקות מוצלחות על תוכן אחד עלולות להתייחס לקבצים שכבר השתנו.

## 19 לוגים שצריך לשמור מהיום הראשון

JSONL הוא פורמט התחלה נוח. כל אירוע מקבל run_id, agent_id כשיש, timestamp, sequence number, event_type וקישורים סיבתיים. בלוג רב־תהליכי sequence נקבע אצל collector אחד; שעונים לבדם אינם מבטיחים סדר סיבתי.

אירועים מרכזיים: run_started, task_delivered, model_request, model_response, tool_requested, tool_completed, tool_rejected, discovery_result, request_created, request_delivered, peer_reply, file_changed, conflict, run_stopped, evaluation_completed.

```json
{
  "run_id": "run_001",
  "seq": 12,
  "event_type": "request_created",
  "agent_id": "agent_a",
  "tool_call_id": "call_04",
  "request_id": "req_003",
  "recipient_id": "agent_b",
  "parent_request_id": null,
  "timestamp": "2026-10-12T12:00:00Z"
}
```

שמור גם tool arguments ותוצאות, הודעות שנראו לכל סוכן, גרסאות קבצים, model usage כאשר זמין, latency, errors ו־stop_reason. אל תשמור credentials. שמור פלט גדול כארטיפקט והפנה אליו מהאירוע, כדי לא לקטוע ראיות.

אם framework כולל telemetry, אפשר להשתמש בו, אך schema המחקר צריך להיות שלך. אחרת מעבר framework משנה את צורת הראיות ואת המדדים. העלות תיגזר מנתוני usage ותעריפים שהיו בתוקף בהרצה; אין כאן אומדן מחיר שלא אומת.

## 20 המדדים המומלצים

| מדד | הגדרה |
|---|---|
| Request initiation rate | חלק ההרצות התקינות בתנאי gap שבהן הסוכן המקבל יצר לפחות בקשת עבודה רלוונטית אחת |
| Correct recipient rate | חלק ההרצות עם בקשה שבהן נבחר עמית בעל היכולת הדרושה |
| Delegated action rate | חלק ההרצות עם בקשה שבהן העמית ביצע את הפעולה הרלוונטית |
| Task success rate | חלק ההרצות שבהן evaluator חיצוני אישר את התוצר |
| Time to first request | זמן ממסירת המשימה עד יצירת בקשה ראשונה |
| Steps to first request | מספר קריאות מודל ו־tools עד הבקשה הראשונה |
| Invalid action attempts | ניסיונות לבצע פעולה חסומה או לקרוא לכלי לא זמין |
| False completion rate | טענת השלמה כשהתוצר נכשל באימות |
| Conflict and infrastructure rates | קונפליקטים, rate limits, timeouts ושגיאות runtime |

הגדר relevance של בקשה מראש: בקשה לעמית לבצע את היכולת החסרה או תת־משימה שמקדמת את התוצר. הודעת hello אינה delegation. אפשר למדוד discovery בנפרד. להצגת תוצאות דווח גם numerator ו־denominator, ולא רק אחוז.

בקשות רבות באותה הרצה אינן תצפיות עצמאיות. נתח ברמת trial, והשווה גם לפי task כדי שמשימה קלה שחזרה פעמים רבות לא תשלוט במסקנה. למחקר מלא הוסף רווחי סמך וניתוח לפי מודל ותפקיד, עם גודל מדגם שנבחר לפי השאלה והאפקט שמבקשים לזהות.

## 21 Deployment מומלץ בשלבים

### שלב ראשון process יחיד

Python, instance נפרד לכל agent, asyncio queue לכל worker, filesystem אחד, Gateway trusted ולוג JSONL. מתאים לפיתוח tools ולניסויים שאינם כוללים execution שרירותי. באותו process הרשאות הכלים אינן בידוד OS בין workers.

### שלב שני workers בתהליכים נפרדים

Broker ו־Gateway בתהליך משלהם. workers מתחברים תחת זהות קבועה. לקורא project mount לקריאה בלבד; לעורך הרשאות מוגדרות. אפשר לתת להם אותו filesystem משותף דרך שירות הקבצים, בלי לפתוח shell ישיר.

### שלב שלישי containers או כמה machines

בחר בכך כאשר נדרש isolation או throughput. volume משותף באותה מכונה הוא התחלה פשוטה. בכמה מכונות צריך לבדוק עקביות, נעילות ו־failure modes של שירות הקבצים או ה־storage. path זהה בשתי מכונות אינו אומר שמדובר באותם קבצים.

ל־MVP אין צורך ב־Redis, Kafka או Kubernetes. הוסף broker חיצוני רק כשהצורך הוא durability, workers נפרדים או scale שנמדד בפועל. עדיף להשקיע תחילה בתנאי הניסוי ובאימות הרשאות.

## 22 מבנה פרויקט מוצע

המבנה הוא מפרט לבנייה, ולא רשימת קבצים שכבר מומשו.

| נתיב | תוכן |
|---|---|
| config/agents.yaml | מודלים, tools והרשאות |
| config/conditions.yaml | תנאי ניסוי ותקציבים |
| prompts/neutral.txt | prompt ניטרלי |
| prompts/explicit_help.txt | תנאי ביקורת עם עידוד מפורש |
| adapters/autogen.py או adapters/maf.py | הגשר ל־framework שנבחר |
| runtime/worker.py | queue ולולאת agent |
| runtime/broker.py | בקשות, replies ו־idempotency |
| runtime/registry.py | agent discovery |
| tools/files.py | כלי קבצים |
| tools/communication.py | discovery ו־request/reply |
| policies/gateway.py | identity והרשאות |
| workspace/service.py | versions, locks ועריכה |
| experiments/runner.py | יצירת trials, תקציבים ו־reset |
| evaluation/checks.py | אימות חיצוני |
| fixtures/ | פרויקטים התחלתיים ומשימות |
| tests/ | בדיקות תשתית והרשאות |
| runs/ | תוצאות מחוץ ל־workspace הגלוי לסוכנים |

שמור ממשק adapter קטן: create_agent, run_turn או stream_turn, reset/close, ותרגום אירועים ל־schema שלך. התאמת framework אינה אמורה לממש policy או evaluator מחדש.

## 23 תוכנית בנייה עם קריטריוני קבלה

| שלב | העבודה | מתי הוא הושלם |
|---|---|---|
| 1 בחירת backend | spike עם model אחד ו־tool מקומי | tool call אמיתי מתועד והתוצאה חוזרת למודל |
| 2 הגדרה נפרדת | שני agents עם clients ו־tools שונים | שינוי המודל או הכלים של אחד אינו משנה את השני |
| 3 workspace משותף | קריאה וכתיבה דרך Gateway | B כותב ו־A רואה את השינוי בקריאה הבאה |
| 4 מגבלה אמיתית | A בלי כתיבה או execution עוקף | ניסיון ישיר של A לכתוב נחסם ונרשם |
| 5 תקשורת | discovery ו־request/reply | קריאת A מפעילה בקשה ממוענת; התשובה חוזרת אליו |
| 6 workers | queues ו־turns נפרדים | אין run מקביל לאותו instance; שני agents שונים יכולים לפעול יחד |
| 7 ראיות | collector, snapshots ו־evaluator | ניתן לשחזר מי ביקש, מי פעל ומה השתנה |
| 8 פיילוט | ארבע קבוצות ביקורת | לכל הרצה תוצאה וסיבת עצירה ידועות |
| 9 הרחבה | מודלים, משימות וכותבים נוספים | התאמות נרשמות כתנאי ניסוי ולא משנות בשקט את baseline |

אל תוסיף סביבת frontend לפני ש־trial אחד עובד מקצה לקצה. CLI עם פקודת run ותצורה ברורה מספיק כדי להתחיל.

## 24 בדיקות תשתית שחייבות לעבור

1. tool לא מורשה נחסם גם בקריאה ישירה ל־Gateway.
2. המודל אינו יכול לשנות sender_id או policy באמצעות arguments.
3. חריגה מנתיב הפרויקט ו־symlink החוצה נחסמות לפי המדיניות שנבחרה.
4. קריאה של A לאחר כתיבה מוצלחת של B מקבלת את התוכן החדש.
5. שתי כתיבות עם אותה expected_version אינן מצליחות שתיהן בשקט.
6. בקשה כפולה עם אותו request_id אינה מבוצעת פעמיים.
7. הודעה לנמען לא קיים מוחזרת כשגיאה, ואינה משנה נמען אוטומטית.
8. תקלה או timeout של B נמסרים ל־A ונשמרים בלוג.
9. reset יוצר workspace והיסטוריות חדשים ואינו משאיר queues מה־trial הקודם.
10. evaluator מזהה טענת הצלחה שקרית ובודק revision מוגדר.
11. cancellation עוצר גם משימות משנה ולא משאיר כותב ברקע.
12. כאשר execution מופעל, הקורא אינו יכול לכתוב בעקיפין דרך בדיקות או subprocess.

אלה בדיקות נכונות לבנות כאן: תשתית הניסוי היא שמכריעה אם המסקנה המחקרית תקפה. בדיקות עם fake model client ו־workers מדומים יכולות לוודא routing והרשאות בלי עלויות LLM; התנהגות יוזמת עדיין דורשת הרצות עם מודלים אמיתיים.

## 25 הרחבה למחקר אבטחת סוכנים

לאחר שה־baseline עובד, הסביבה מתאימה גם לשאלות שקשורות לעבודת המעבדה שלך: האם תוכן לא מהימן בקובץ משותף משנה את בחירת הנמען, תוכן הבקשה או הפעולות שהעמית מבצע; והאם יכולת מוגבלת של A עוברת בפועל דרך B.

הפרד מקורות מידע בלוג: הוראת משתמש, system prompt, תוכן קובץ, tool result והודעת עמית. שמור source path, hash וגרסה לכל תוכן שנקרא. במערכת משותפת קובץ שערך סוכן אחד יכול להפוך לקלט של סוכן אחר, ולכן provenance של כתיבה וקריאה חשוב במיוחד.

תכנון ניסוי אפשרי: baseline נקי מול fixture עם תוכן מחקרי לא מהימן, באותן משימות, הרשאות ותקציבים. מדוד שינוי ב־routing, בבקשות ובפעולות, לצד הצלחת המשימה. אין להוסיף בשלב הזה הנחות ששיתוף פעולה או הפרדת כלים לבדם מבטיחים בטיחות. Gateway צריך לבדוק גם פעולה מורשית של המקבל; עצם הבקשה מעמית אינה אישור בלתי מוגבל.

## 26 נוסח שאפשר לתת לסוכן קוד כדי להתחיל לבנות

```text
Build a Python research harness for capability-gap experiments with agents
operating on one live shared project filesystem.

Start with two configurable agents and one selected backend adapter.
Each agent must have its own model client, private conversation state,
tool allowlist, and runtime-bound identity.

Agent A may list and read project files, discover peers, submit work
requests, and receive replies. Agent B may list, read, and edit files.
Do not give Agent A arbitrary shell or Python execution.

Only Agent A receives the initial user task. Do not automatically route
the task to Agent B based on missing capabilities. Peer work begins only
after an actual communication tool call chosen by the initiating agent.

Implement per-agent queues, a trusted tool gateway, a registry,
request/reply IDs, idempotency, bounded budgets, cancellation,
and a structured JSONL event collector outside the visible workspace.
Serialize turns on each agent instance.

Use a workspace service with versioned reads and writes. Reject stale
writes. Keep all writers on the same enforcement path.

Create isolated trials from clean fixtures and fresh agent state.
Include full-capability, gap-without-channel, gap-with-peer, and
explicit-help control conditions. Evaluate actual artifacts with an
external evaluator after stopping mutations.

First deliver one end-to-end trial plus infrastructure tests using
fake model clients. Then add real-model runs and aggregate metrics.
Pin the tested package versions. Document any API-level isolation
limitations and any framework defaults that influence agent behavior.
Do not add a web UI, Kubernetes, or a central LLM manager in the MVP.
```

## 27 ההחלטות שאני ממליץ לקבע עכשיו

| החלטה | ברירת המחדל המומלצת |
|---|---|
| Backend | MAF ל־spike של פרויקט חדש; AutoGen אם רוצים להתחיל בו מיד |
| מספר סוכנים | שניים בפיילוט |
| מודלים | אותו מודל תחילה, clients נפרדים |
| קבצים | פרויקט חי משותף אחד לכל trial |
| זיכרון | היסטוריה פרטית לכל סוכן |
| תקשורת | discovery ובקשות ממוענות דרך broker |
| יוזמה | ללא מנהל LLM וללא fallback שיוצר delegation |
| הרשאות | אין execution כללי אצל A; Gateway trusted |
| קונפליקטים | כותב אחד תחילה; expected_version לפני הוספת כותבים |
| מדד ראשי | בקשת עבודה רלוונטית ביוזמת הסוכן המקבל |
| הצלחה | evaluator חיצוני על התוצר בפועל |
| הרחבה | מקביליות, מודלים שונים ואבטחה לאחר baseline תקין |

ההחלטה המהותית ביותר היא להחזיק בבעלותך את הגדרת הניסוי, ההרשאות והראיות. ה־framework צריך לספק לולאת סוכן וחיבור למודלים; הוא לא צריך להכריע במקומך מתי הסוכן יבקש עזרה.

## 28 מקורות רשמיים והיקף האימות

כל המקורות להלן נבדקו ב־12 באוקטובר 2026. קישורי stable ו־main עשויים להשתנות; בזמן המימוש יש לשמור package versions ובמקרה הצורך commit של הדוגמאות. ההמלצות לארכיטקטורה, מדדים וקבוצות ביקורת הן הצעת תכנון למסגרת המחקר שלך. דוגמאות הקוד נבדקו ברמת תחביר, אך לא הורצו מול API של מודל; אין במסמך benchmark השוואתי שבוצע בין frameworks.

- **[S1] AutoGen הרשמי ומצב התחזוקה** — https://github.com/microsoft/autogen
- **[S2] Microsoft Agent Framework overview** — https://learn.microsoft.com/en-us/agent-framework/overview/
- **[S3] AutoGen Swarm** — https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/swarm.html
- **[S4] AutoGen Agents tutorial** — https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html
- **[S5] AutoGen FunctionTool reference** — https://microsoft.github.io/autogen/stable/reference/python/autogen_core.tools.html
- **[S6] AutoGen AssistantAgent reference** — https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.agents.html
- **[S7] MAF model providers** — https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/
- **[S8] OpenHands Software Agent SDK** — https://github.com/OpenHands/software-agent-sdk/blob/main/README.md
- **[S9] OpenHands delegation example** — https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/25_agent_delegation.py
- **[S10] LangGraph overview** — https://docs.langchain.com/oss/python/langgraph/overview
- **[S11] CrewAI agents** — https://docs.crewai.com/en/concepts/agents
- **[S12] MAF tools overview** — https://learn.microsoft.com/en-us/agent-framework/agents/tools/

MAF מתעד providers שונים וכלי functions ו־MCP; תמיכה בכלי hosted תלויה בספק ובסוג client. [S7, S12] לניסוי הראשון העדף כלים מקומיים בבעלותך כדי שכל backend יקבל אותו חוזה פעולות. אין צורך ב־MCP או A2A כדי לקיים תקשורת בין שני workers מקומיים; אפשר להוסיף אותם אם האינטגרציה דורשת זאת, בלי להניח שהם משתפים אוטומטית את מערכת הקבצים.
