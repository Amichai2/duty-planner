import io,json
from datetime import datetime, date, time, timedelta
import pandas as pd
import streamlit as st
from openpyxl.styles import Font,PatternFill
from solver import example,solve,audit
from timeline_pdf import build_timeline_pdf

# UI clock-time adapter. The solver continues to use integer relative hours.
DT_FMT = '%Y-%m-%d %H:%M'

def normalize_clock_config(config):
    """Migrate legacy JSON without modifying its relative time windows."""
    if 'start_date' not in config:
        config['start_date'] = date.today().isoformat()
    if 'start_hour' not in config:
        config['start_hour'] = (6 + int(config.get('start_offset_hours', 0))) % 24
    config['start_offset_hours'] = (int(config['start_hour']) - 6) % 24
    return config

def planning_start(config):
    normalize_clock_config(config)
    return datetime.combine(date.fromisoformat(str(config['start_date'])), time(int(config['start_hour'])))

def display_hour(config, relative):
    return (planning_start(config) + timedelta(hours=int(relative))).strftime(DT_FMT)

def parse_hour(config, value):
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=None)
    else:
        dt = datetime.strptime(str(value).strip(), DT_FMT)
    delta = (dt - planning_start(config)).total_seconds() / 3600
    if not delta.is_integer():
        raise ValueError('יש להזין שעות עגולות בלבד, למשל 2026-10-20 11:00')
    return int(delta)

def parse_windows(config, text):
    """Each line is 'YYYY-MM-DD HH:00 | YYYY-MM-DD HH:00'."""
    result=[]
    for line in str(text).splitlines():
        if not line.strip(): continue
        a,b=[x.strip() for x in line.split('|')]
        result.append([parse_hour(config,a),parse_hour(config,b)])
    return result

def windows_text(config, windows):
    return '\n'.join(f'{display_hour(config,a)} | {display_hour(config,b)}' for a,b in windows)

st.set_page_config(page_title='Duty Planner | תכנון איושים',page_icon='📅',layout='wide')
st.markdown('''<style>.block-container{padding-top:1.3rem;max-width:1450px}h1,h2,h3{direction:rtl} .stMetric{background:#f1f6f8;border-radius:12px;padding:12px}</style>''',unsafe_allow_html=True)
st.title('Duty Planner · מערכת תכנון איושים')
st.caption('אופטימיזציה אמיתית באמצעות OR-Tools CP-SAT | תכנון, זמינות, בקרה, עומסים וייצוא')
if 'config' not in st.session_state:st.session_state.config=normalize_clock_config(example())
if 'result' not in st.session_state:st.session_state.result=None
c=normalize_clock_config(st.session_state.config)

with st.sidebar:
    st.header('תרחישים ושיתוף')
    f=st.file_uploader('ייבוא תרחיש JSON',type='json')
    if f and st.button('טען תרחיש'):
        try:st.session_state.config=normalize_clock_config(json.load(f));st.session_state.result=None;st.rerun()
        except Exception as e:st.error(str(e))
    if st.button('איפוס לתרחיש לדוגמה'):
        st.session_state.config=normalize_clock_config(example());st.session_state.result=None;st.rerun()
    st.download_button('⬇️ הורד הגדרות לשיתוף',json.dumps(c,ensure_ascii=False,indent=2).encode('utf-8'),'scenario.json','application/json')
    st.info('שיתוף: פרסמו את האפליקציה ב-Streamlit Community Cloud או שרת פרטי. אפשר להעביר תרחישים בין משתמשים כקובצי JSON.')

tabs=st.tabs(['👥 כוח אדם וזמינות','⚙️ משימות ואילוצים','📜 איושים קודמים','▶️ אופטימיזציה','📊 דשבורד ותכנית','🔍 בדיקת תקינות'])
with tabs[0]:
    st.subheader('חיילים, צוותים, נהג וחלונות זמינות')
    st.write('זמינות לפי תאריך ושעת שעון. כל שורה בתא היא חלון: `2026-10-20 11:00 | 2026-10-21 11:00`. אפשר להזין כמה חלונות בשורות נפרדות.')
    df=pd.DataFrame([{'חייל':p['id'],'צוות':str(p['team']),'נהג':bool(p.get('driver')),'זמינות':windows_text(c,p.get('availability',[[0,c['hours']]]))} for p in c['people']])
    edited=st.data_editor(df,num_rows='dynamic',hide_index=True,use_container_width=True,key=f"people_editor_{c['start_date']}_{c['start_hour']}")
    if st.button('שמור כוח אדם וזמינות'):
        try:
            new=[]
            for _,r in edited.iterrows():
                if pd.isna(r['חייל']) or not str(r['חייל']).strip():continue
                windows=[]
                windows=parse_windows(c,r['זמינות'])
                new.append({'id':str(r['חייל']).strip(),'team':str(r['צוות']).strip(),'driver':bool(r['נהג']),'availability':windows})
            if len({p['id'] for p in new})!=len(new):raise ValueError('מזהי חיילים כפולים')
            c['people']=new
            selected=[p['id'] for p in new if p['driver']]
            if selected:c['driver']=selected[0]
            st.session_state.result=None;st.success('נשמר')
        except Exception as e:st.error(f'שגיאה: {e}')
with tabs[1]:
    st.subheader('פרמטרים של משימות ומדיניות')
    a,b,d=st.columns(3)
    with a:
        c['hours']=st.number_input('אורך התכנון בשעות',8,168,int(c['hours']),step=8)
        c['start_date']=st.date_input('תאריך תחילת הסידור',value=date.fromisoformat(str(c['start_date']))).isoformat()
        c['start_hour']=st.selectbox('שעת התחלה (שעות עגולות)',list(range(24)),index=int(c['start_hour']),format_func=lambda h:f'{h:02d}:00')
        c['start_offset_hours']=(int(c['start_hour'])-6)%24
        st.caption(f"טווח התכנון: {display_hour(c,0)} עד {display_hour(c,int(c['hours']))}. הסיורים והש״ג מתחילים בשעת ההתחלה.")
        c['tour_size']=st.number_input('לוחמים בסיור',1,12,int(c['tour_size']))
        c['tour_length']=st.number_input('משך משמרת סיור (שעות)',1,24,int(c['tour_length']))
        c['gate_length']=st.number_input('משך משמרת ש״ג (שעות)',1,12,int(c['gate_length']))
    with b:
        teams=sorted({str(p['team']) for p in c['people']})
        options=teams+['variable']
        c['carmel_team']=st.selectbox('צוות כרמל',options,index=options.index(str(c['carmel_team'])) if str(c['carmel_team']) in options else 0,format_func=lambda x:'משתנה — חלוקה יחסית' if x=='variable' else f'צוות {x}')
        if c['carmel_team']=='variable':st.caption('ארבעת הלוחמים יהיו מאותו צוות בכל שעה; יחס האיוש יותאם לשעות הזמינות של הצוותים.')
        c['carmel_size']=st.number_input('מספר לוחמי כרמל (ללא נהג)',0,12,int(c['carmel_size']))
        people_ids=[p['id'] for p in c['people']]
        c['driver']=st.selectbox('נהג קבוע',people_ids,index=people_ids.index(c['driver']) if c['driver'] in people_ids else 0)
        dep=st.text_input('יציאות כרמל, שעות שעון אמיתיות (0–23)',','.join(map(str,c['carmel_departures'])))
        try:c['carmel_departures']=sorted({int(x.strip()) for x in dep.split(',') if x.strip() and 0<=int(x.strip())<24})
        except ValueError:st.warning('שעות היציאה חייבות להיות מספרים שלמים בין 0 ל־23')
        c['carmel_exit_length']=st.number_input('משך יציאת כרמל (שעות)',1,6,int(c.get('carmel_exit_length',1)))
    with d:
        c['min_rest']=st.number_input('מנוחה קשיחה בין סיור/ש״ג',0,24,int(c['min_rest']))
        c['target_rest']=st.number_input('יעד מנוחה רך (שעות)',0,24,int(c['target_rest']))
        c['carmel_rest']=st.number_input('מנוחה קשיחה סביב יציאת כרמל',0,24,int(c['carmel_rest']))
        c['hard_no_repeat_tour_night']=st.checkbox('איסור סיור לילה בלילות רצופים',bool(c['hard_no_repeat_tour_night']))
        c['hard_no_repeat_any_night']=st.checkbox('איסור פעילות לילה בלילות רצופים',bool(c['hard_no_repeat_any_night']))
        c['minimize_carmel_changes']=st.checkbox('מזעור חילופי כרמל',bool(c['minimize_carmel_changes']))
        c['enable_patrol_rest_target']=st.checkbox('הפעל יעד מנוחה בין סיורים',bool(c.get('enable_patrol_rest_target',True)))
        c['patrol_rest_target']=st.number_input('יעד שעות מנוחה מסיום סיור לתחילת הבא',0,48,int(c.get('patrol_rest_target',16)))
        c['enable_carmel_share']=st.checkbox('איזון יחסי של כרמל בין הצוותים',bool(c.get('enable_carmel_share',True)),disabled=c['carmel_team']!='variable')
    with st.expander('משקלי עומס ומגבלת חיפוש'):
        x,y,z,w=st.columns(4)
        c['tour_weight']=x.number_input('משקל סיור',1,10,int(c['tour_weight']))
        c['gate_weight']=y.number_input('משקל ש״ג',1,10,int(c['gate_weight']))
        c['carmel_weight']=z.number_input('משקל יציאת כרמל',0,10,int(c['carmel_weight']))
        c['night_weight']=w.number_input('תוספת לשעת לילה',0,10,int(c['night_weight']))
        c['time_limit']=st.slider('זמן חיפוש (שניות)',5,180,int(c['time_limit']),5)
    st.info('כרמל: שעות שעון אמיתיות (ברירת מחדל 06:00 ו־18:00). לילה: תמיד 00:00–06:00. זמינות והיסטוריה מוצגות כתאריכים ושעות שעון; המנוע ממשיך לחשב שעות יחסיות.')
with tabs[2]:
    st.subheader('איושים קודמים — היסטוריה חלקית נתמכת')
    st.info('הזינו משימות עבר לפי תאריך ושעת שעון, בשעות עגולות. אין חובה להזין את כל המשימות. רשומות עבר צריכות להסתיים לכל המאוחר בתחילת הסידור.')
    c['history_completeness']=st.selectbox('שלמות ההיסטוריה', ['partial','complete'],index=0 if c.get('history_completeness','partial')=='partial' else 1,format_func=lambda x:'חלקית — אין להסיק שהחייל נח' if x=='partial' else 'מלאה — כל המשימות מתועדות')
    history_df=pd.DataFrame([{'חייל':x['soldier'],'משימה':x['task'],'התחלה':display_hour(c,x['start']),'סיום':display_hour(c,x['end'])} for x in c.get('history',[])],columns=['חייל','משימה','התחלה','סיום'])
    history_edit=st.data_editor(history_df,num_rows='dynamic',hide_index=True,use_container_width=True,key=f"history_editor_{c['start_date']}_{c['start_hour']}")
    upload=st.file_uploader('ייבוא היסטוריה מקובץ CSV או Excel',type=['csv','xlsx'],key='history_upload')
    if upload and st.button('טען היסטוריה מהקובץ'):
        try:
            loaded=pd.read_csv(upload) if upload.name.endswith('.csv') else pd.read_excel(upload)
            required=['חייל','משימה','התחלה','סיום']
            if not all(x in loaded.columns for x in required):raise ValueError('נדרשות עמודות: '+', '.join(required))
            c['history']=[{'soldier':str(r['חייל']).strip(),'task':str(r['משימה']).strip(),'start':parse_hour(c,r['התחלה']),'end':parse_hour(c,r['סיום'])} for _,r in loaded.iterrows() if pd.notna(r['חייל'])]
            st.session_state.result=None
            st.rerun()
        except Exception as e:st.error(str(e))
    if st.button('שמור היסטוריה'):
        try:
            c['history']=[{'soldier':str(r['חייל']).strip(),'task':str(r['משימה']).strip(),'start':parse_hour(c,r['התחלה']),'end':parse_hour(c,r['סיום'])} for _,r in history_edit.iterrows() if pd.notna(r['חייל']) and str(r['חייל']).strip()]
            st.session_state.result=None
            st.success(f"נשמרו {len(c['history'])} משימות קודמות")
        except Exception as e:st.error(str(e))
    st.download_button('⬇️ תבנית CSV להיסטוריה',pd.DataFrame([{'חייל':'A1','משימה':'סיור','התחלה':display_hour(c,-8),'סיום':display_hour(c,0)}]).to_csv(index=False).encode('utf-8-sig'),'history_template.csv','text/csv')
    st.caption('כרמל היסטורי מציין הגדרה בלבד, ואינו נחשב ליציאה פעילה. בגרסה זו נטענים רק איושים שהסתיימו לפני תחילת התכנון; נעילת איושים עתידיים אינה כלולה.')
with tabs[3]:
    st.subheader('הרצת אופטימיזציה')
    st.write('המנוע מחפש פתרון המכסה את המשימות ללא חפיפות, עם צוותים אורגניים, זמינות אישית ומנוחה קשיחה. לאחר מכן הוא משפר מנוחה, איזון עומסים ויציבות כרמל.')
    if st.button('🚀 הרץ אופטימיזציה',type='primary',use_container_width=True):
        try:
            with st.spinner('מחשב סידור עבודה...'):
                st.session_state.result=solve(c)
            st.success(f"סטטוס: {st.session_state.result['status']}") if 'shifts' in st.session_state.result else st.error(st.session_state.result['message'])
        except Exception as e:st.error(str(e))
    if st.session_state.result:st.json({k:v for k,v in st.session_state.result.items() if k not in ('shifts','metrics')})
with tabs[4]:
    r=st.session_state.result
    if not r or 'shifts' not in r:st.info('יש להריץ אופטימיזציה תחילה.')
    else:
        shifts=pd.DataFrame(r['shifts']);shifts['חיילים']=shifts['soldiers'].apply(lambda x:', '.join(x))
        shifts['משימה']=shifts['task'];shifts['תחילה (שעה)']=shifts['start'];shifts['סיום (שעה)']=shifts['end'];shifts['צוות']=shifts['team']
        def clock_label(t):return display_hour(c,t)
        shifts['תחילה (שעון)']=shifts['start'].map(clock_label);shifts['סיום (שעון)']=shifts['end'].map(clock_label)
        met=pd.DataFrame(r['metrics']);x,y,z,w=st.columns(4)
        x.metric('חיילים',len(met));y.metric('משמרות סיור',sum(shifts['task']=='סיור'));z.metric('משמרות ש״ג',sum(shifts['task']=='ש״ג'));w.metric('פעילות לילה (שעות)',int(met['לילה 00–06 (שעות)'].sum()))
        # Normalize metrics from older solver versions and recompute employment rates.
        # Use the canonical v4 column names; never assume the rate column exists.
        if 'זמינות (שעות)' not in met.columns:
            st.error('נתוני זמינות חסרים בפלט המנוע. יש לעדכן גם את solver.py.')
            st.stop()
        if 'פעילות בפועל (שעות)' not in met.columns:
            needed=['סיור (שעות)','ש״ג (שעות)','יציאות כרמל']
            missing=[name for name in needed if name not in met.columns]
            if missing:
                st.error('עמודות פעילות חסרות בפלט המנוע: '+', '.join(missing)+'. יש לעדכן גם את solver.py.')
                st.stop()
            exit_length=float(c.get('carmel_exit_length',1))
            met['פעילות בפועל (שעות)']=(
                pd.to_numeric(met['סיור (שעות)'],errors='coerce').fillna(0)
                +pd.to_numeric(met['ש״ג (שעות)'],errors='coerce').fillna(0)
                +pd.to_numeric(met['יציאות כרמל'],errors='coerce').fillna(0)*exit_length
            )
            if 'נהג' in met.columns:
                departure_count=len(r.get('departures',[]))
                met['פעילות בפועל (שעות)']+=met['נהג'].fillna(False).astype(bool).astype(int)*departure_count*exit_length
        available=pd.to_numeric(met['זמינות (שעות)'],errors='coerce')
        active=pd.to_numeric(met['פעילות בפועל (שעות)'],errors='coerce')
        met['אחוז תעסוקה']=(100*active/available.where(available>0)).round(2)
        rates=met['אחוז תעסוקה'].dropna()
        a1,a2=st.columns(2)
        a1.metric('ממוצע אחוז תעסוקה לחייל',f'{rates.mean():.1f}%' if len(rates) else '—')
        available_total=met['זמינות (שעות)'].sum()
        a2.metric('אחוז תעסוקה משוקלל לפי זמינות',f"{100*met['פעילות בפועל (שעות)'].sum()/available_total:.1f}%" if available_total else '—')
        if c.get('history') and c.get('history_completeness')=='partial':st.warning('היסטוריית האיושים חלקית: מדדי מנוחה ולילות אינם מאומתים ביחס למשימות עבר שלא הוזנו.')
        st.subheader('סידור עבודה')
        st.dataframe(shifts[['תחילה (שעון)','סיום (שעון)','משימה','צוות','חיילים']],hide_index=True,use_container_width=True,height=380)
        st.subheader('עומס לכל חייל')
        st.bar_chart(met.set_index('חייל')[['אחוז תעסוקה']])
        st.bar_chart(met.set_index('חייל')[['סיור (שעות)','ש״ג (שעות)','לילה 00–06 (שעות)']])
        st.dataframe(met,hide_index=True,use_container_width=True)
        if c['carmel_team']=='variable':
            st.subheader('חלוקת כרמל בין הצוותים')
            ch=r.get('carmel_team_hours',{});tot=sum(ch.values())
            st.dataframe(pd.DataFrame([{'צוות':g,'שעות איוש בפועל':n,'אחוז בפועל':round(100*n/tot,1) if tot else 0,'יעד אחוז':r.get('carmel_target_pct',{}).get(g,0)} for g,n in ch.items()]),hide_index=True,use_container_width=True)
        try:
            pdf_bytes=build_timeline_pdf(c,r)
            st.download_button('⬇️ הורד PDF — ציר זמן לכל חייל',pdf_bytes,'duty_activity_timeline.pdf','application/pdf')
        except Exception as e:st.warning(f'לא ניתן ליצור PDF: {e}')
        output=io.BytesIO()
        with pd.ExcelWriter(output,engine='openpyxl') as writer:
            shifts[['תחילה (שעון)','סיום (שעון)','משימה','צוות','חיילים']].to_excel(writer,sheet_name='איושים',index=False)
            met.to_excel(writer,sheet_name='עומסים',index=False)
            pd.DataFrame([{'חייל':h['soldier'],'משימה':h['task'],'התחלה':display_hour(c,h['start']),'סיום':display_hour(c,h['end'])} for h in c.get('history',[])],columns=['חייל','משימה','התחלה','סיום']).to_excel(writer,sheet_name='היסטוריה',index=False)
            pd.DataFrame(audit(c,r)).to_excel(writer,sheet_name='בדיקת תקינות',index=False)
            pd.DataFrame([{'פרמטר':k,'ערך':json.dumps(v,ensure_ascii=False)} for k,v in c.items() if k!='people']).to_excel(writer,sheet_name='פרמטרים',index=False)
            for sheet in writer.book:
                sheet.sheet_view.showGridLines=False
                sheet.freeze_panes='A2'
                for cell in sheet[1]:cell.fill=PatternFill('solid',fgColor='16324F');cell.font=Font(color='FFFFFF',bold=True)
                for col in sheet.columns:
                    letter=col[0].column_letter
                    sheet.column_dimensions[letter].width=min(50,max(15,max(len(str(v.value or '')) for v in list(col)[:100])+2))
        st.download_button('⬇️ הורד Excel מלא',output.getvalue(),'duty_plan.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('⬇️ הורד תוצאות JSON',json.dumps(r,ensure_ascii=False,indent=2).encode(),'result.json','application/json')
with tabs[5]:
    r=st.session_state.result
    if not r or 'shifts' not in r:st.info('יש להריץ אופטימיזציה תחילה.')
    else:
        checks=audit(c,r)
        if all(x['status']=='PASS' for x in checks):st.success('בדיקות כיסוי, זמינות, חפיפה וצוות אורגני עברו בהצלחה.')
        else:st.error('נמצאו הפרות')
        st.dataframe(pd.DataFrame(checks),hide_index=True,use_container_width=True)
        st.caption('אילוצי המנוחה והלילות נאכפים ישירות במודל; הבדיקה העצמאית כאן בודקת כיסוי, זמינות, חפיפות ואורגניות. אין להסתמך על תכנון זה ללא אישור אנושי ובדיקת כשירות, עייפות ונהלים.')
