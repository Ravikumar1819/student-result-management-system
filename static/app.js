let csrf = '', currentUser = null;
const $ = id => document.getElementById(id);
async function api(path, method='GET', payload) {
  const response = await fetch('/api' + path, {method, headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:payload ? JSON.stringify(payload) : undefined});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed. Try again.');
  if (result.csrf) csrf = result.csrf;
  return result;
}
function message(text, error=false) { $('message').textContent=text; $('message').className='notice'+(error?' error':''); $('message').hidden=!text; }
function element(tag, text, parent) { const node=document.createElement(tag); node.textContent=text; if(parent)parent.append(node); return node; }
function action(label, handler, parent, style='') { const b=element('button',label,parent); b.type='button'; b.className=style; b.onclick=()=>Promise.resolve(handler()).catch(e=>message(e.message,true)); return b; }
async function authenticate(register=false) {
  try {
    const payload={username:$('username').value,password:$('password').value};
    if(register){const r=await api('/register','POST',payload);message(r.message);return;}
    const result=await api('/login','POST',payload);currentUser=result.user;$('password').value='';await showApp();message('');
  } catch(e) {message(e.message,true);}
}
async function showApp() {
  $('auth').hidden=!!currentUser;$('workspace').hidden=!currentUser;
  $('account').textContent=currentUser ? 'Signed in as '+currentUser.username : '';
  if(currentUser) await load();
}
async function initialize() {
  try { const state=await api('/session');currentUser=state.user;await showApp(); } catch(e){message(e.message,true);}
  $('login').onsubmit=e=>{e.preventDefault();authenticate();};
  $('register').onclick=()=>authenticate(true);
  $('logout').onclick=async()=>{try{await api('/logout','POST');location.reload();}catch(e){message(e.message,true);}};
}

let studentId=null, examId=null;
function options(id, items, label) {const s=$(id);s.replaceChildren();for(const item of items){const o=element('option',label(item),s);o.value=item.id ?? '';}}
async function load(){
  const r=await api('/records'), isAdmin=currentUser.role==='admin';$('admin-tools').hidden=!isAdmin;
  options('student-user',[{id:null,username:'No linked account'},...r.users],x=>x.username);
  options('result-student',r.students,x=>x.roll+' / '+x.name);options('result-exam',r.exams,x=>x.name+' / '+x.subject);
  $('student-rows').replaceChildren();$('exam-rows').replaceChildren();$('result-rows').replaceChildren();
  for(const s of r.students){const tr=element('tr','',$('student-rows'));element('td',s.roll,tr);element('td',s.name,tr);const td=element('td','',tr);if(isAdmin){action('Edit',()=>{studentId=s.id;$('roll').value=s.roll;$('student-name').value=s.name;$('student-user').value=s.user_id??'';$('save-student').textContent='Save student';$('roll').focus();},td,'secondary');action('Delete',async()=>{if(confirm('Delete this student and all their results?')){await api('/students/'+s.id,'DELETE');await load();}},td,'danger');}}
  for(const e of r.exams){const tr=element('tr','',$('exam-rows'));element('td',e.name,tr);element('td',e.subject,tr);const td=element('td','',tr);if(isAdmin){action('Edit',()=>{examId=e.id;$('exam-name').value=e.name;$('subject').value=e.subject;$('save-exam').textContent='Save examination';$('exam-name').focus();},td,'secondary');action('Delete',async()=>{if(confirm('Delete this examination and its results?')){await api('/exams/'+e.id,'DELETE');await load();}},td,'danger');}}
  for(const x of r.results){const tr=element('tr','',$('result-rows'));for(const v of [x.student,x.exam,x.subject,x.score,x.grade])element('td',v,tr);const td=element('td','',tr);if(isAdmin)action('Remove',async()=>{if(confirm('Remove this result?')){await api('/results/'+x.student_id+'/'+x.exam_id,'DELETE');await load();}},td,'danger');}
  const avg=r.results.length ? (r.results.reduce((a,b)=>a+b.score,0)/r.results.length).toFixed(1) : '—';
  $('summary').textContent=r.students.length+' student(s), '+r.results.length+' subject result(s). Average score: '+avg+'.'+(!r.students.length?' Ask your administrator to link your student record.':'');
}
$('student-form').onsubmit=async e=>{e.preventDefault();try{await api('/students'+(studentId?'/'+studentId:''),studentId?'PUT':'POST',{roll:$('roll').value,name:$('student-name').value,user_id:$('student-user').value?Number($('student-user').value):null});$('cancel-student').click();await load();message('Student saved.');}catch(e){message(e.message,true);}};
$('cancel-student').onclick=()=>{studentId=null;$('student-form').reset();$('save-student').textContent='Add student';};
$('exam-form').onsubmit=async e=>{e.preventDefault();try{await api('/exams'+(examId?'/'+examId:''),examId?'PUT':'POST',{name:$('exam-name').value,subject:$('subject').value});$('cancel-exam').click();await load();message('Examination saved.');}catch(e){message(e.message,true);}};
$('cancel-exam').onclick=()=>{examId=null;$('exam-form').reset();$('save-exam').textContent='Add examination';};
$('result-form').onsubmit=async e=>{e.preventDefault();try{await api('/results','PUT',{student_id:Number($('result-student').value),exam_id:Number($('result-exam').value),score:Number($('score').value)});await load();message('Result saved.');}catch(e){message(e.message,true);}};
$('print').onclick=()=>window.print();initialize();
