
(function(){
var t=document.querySelector('.theme');try{var saved=localStorage.getItem('theme');if(saved)document.documentElement.setAttribute('data-theme',saved);}catch(e){}
if(t){t.addEventListener('click',function(){var cur=document.documentElement.getAttribute('data-theme');var dark=cur?cur==='dark':matchMedia('(prefers-color-scheme:dark)').matches;var next=dark?'light':'dark';document.documentElement.setAttribute('data-theme',next);try{localStorage.setItem('theme',next)}catch(e){}});}
/* showcase: vertical = series (steps), horizontal = photos within the active series */
var steps=[].slice.call(document.querySelectorAll('.step')),items=[].slice.call(document.querySelectorAll('.list li')),cnt=document.querySelector('.count'),openA=document.querySelector('.hint a.open');
var sets=[].slice.call(document.querySelectorAll('.stage .set'));
var flat=[].slice.call(document.querySelectorAll('.stage img'));
var cur=0,pos=[],lock=0;sets.forEach(function(){pos.push(0)});
function load(im){if(im&&im.dataset.src){im.src=im.dataset.src;delete im.dataset.src;}}
function render(){
  if(sets.length){sets.forEach(function(st,k){var ims=st.children;for(var j=0;j<ims.length;j++){ims[j].classList.toggle('on',k===cur&&j===pos[cur]);}
      if(k===cur){load(ims[pos[k]]);load(ims[pos[k]+1]);load(ims[pos[k]+2]);load(ims[pos[k]-1]);}else if(Math.abs(k-cur)===1){load(ims[0]);}});
    if(cnt)cnt.textContent=(pos[cur]+1)+' / '+sets[cur].children.length;
    if(openA)openA.setAttribute('href',sets[cur].dataset.href);}
  else{flat.forEach(function(im,k){im.classList.toggle('on',k===cur);});[cur,cur+1,cur+2,cur-1].forEach(function(j){load(flat[j])});if(cnt)cnt.textContent=(cur+1)+' / '+flat.length;}
  items.forEach(function(li,k){li.classList.toggle('on',k===cur);});
}
function series(d){var n=Math.min(Math.max(cur+d,0),steps.length-1);if(n===cur)return;cur=n;if(sets.length)pos[cur]=0;render();steps[n].scrollIntoView({behavior:'smooth'});}
function photo(d){if(!sets.length){series(d);return;}var n=sets[cur].children.length;var p=Math.min(Math.max(pos[cur]+d,0),n-1);if(p===pos[cur])return;pos[cur]=p;render();}
if(steps.length){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){var n=+e.target.dataset.i;if(n!==cur){cur=n;if(sets.length)pos[cur]=0;render();}}});},{threshold:.5});
  steps.forEach(function(st){io.observe(st);});render();
  items.forEach(function(li,k){var a=li.querySelector('a');if(a&&a.getAttribute('href')==='#')a.addEventListener('click',function(e){e.preventDefault();series(k-cur);});});
  document.addEventListener('keydown',function(e){var lb=document.getElementById('lb');if(lb&&lb.classList.contains('on'))return;
    if(e.key==='ArrowRight'){e.preventDefault();photo(1);}else if(e.key==='ArrowLeft'){e.preventDefault();photo(-1);}
    else if(e.key==='ArrowDown'||e.key==='PageDown'||e.key===' '){e.preventDefault();series(1);}else if(e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();series(-1);}
    else if(e.key==='Home'){series(-cur);}else if(e.key==='End'){series(steps.length);}
    else if(e.key==='Enter'&&sets.length){location.href=sets[cur].dataset.href;}});
  window.addEventListener('wheel',function(e){if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)||Math.abs(e.deltaX)<25)return;e.preventDefault();var now=Date.now();if(now-lock<500)return;lock=now;photo(e.deltaX>0?1:-1);},{passive:false});
  var tx=null,ty=null;window.addEventListener('touchstart',function(e){tx=e.touches[0].clientX;ty=e.touches[0].clientY;},{passive:true});
  window.addEventListener('touchend',function(e){if(tx===null)return;var dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;tx=null;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy))photo(dx<0?1:-1);},{passive:true});
  var stage=document.querySelector('.stage');if(stage)stage.addEventListener('click',function(e){if(e.target.tagName!=='IMG')return;var r=stage.getBoundingClientRect();if(e.clientX<r.left+r.width*.3)photo(-1);else photo(1);});
}
/* preloader */
var pre=document.getElementById('pre');
if(pre){var pct=pre.querySelector('.pct'),pile=[].slice.call(pre.querySelectorAll('.pile img')),n=0,total=Math.max(pile.length,1),shown=false;
function done(){if(shown)return;shown=true;pct.textContent='100%';setTimeout(function(){pre.classList.add('out');document.body.style.overflow='';},350);}
document.body.style.overflow='hidden';
pile.forEach(function(im,k){var rot=(k*47)%40-20,dx=(k*31)%50-25,dy=(k*17)%50-25;im.style.transform='translate('+dx+'%,'+dy+'%) rotate('+rot+'deg)';
function tick(){n++;pct.textContent=Math.round(n/total*100)+'%';setTimeout(function(){im.classList.add('in')},k*120);if(n>=total)setTimeout(done,700);}
if(im.complete)tick();else{im.addEventListener('load',tick);im.addEventListener('error',tick);}});
setTimeout(done,4500);}
/* lightbox for grids */
var links=[].slice.call(document.querySelectorAll('[data-full]'));if(!links.length)return;
var lb=document.createElement('div');lb.id='lb';lb.innerHTML='<button class="prev" aria-label="Previous">&#8249;</button><img alt=""><button class="next" aria-label="Next">&#8250;</button><button class="x" aria-label="Close">&times;</button>';
document.body.appendChild(lb);var img=lb.querySelector('img'),i=0;
function show(n){i=(n+links.length)%links.length;img.src=links[i].getAttribute('data-full');lb.classList.add('on');document.body.style.overflow='hidden';}
function hide(){lb.classList.remove('on');document.body.style.overflow='';}
links.forEach(function(a,n){a.addEventListener('click',function(e){e.preventDefault();show(n);});});
lb.querySelector('.prev').onclick=function(e){e.stopPropagation();show(i-1)};lb.querySelector('.next').onclick=function(e){e.stopPropagation();show(i+1)};
lb.querySelector('.x').onclick=function(e){e.stopPropagation();hide()};lb.onclick=function(e){if(e.target===lb||e.target===img)hide()};
document.addEventListener('keydown',function(e){if(!lb.classList.contains('on'))return;if(e.key==='Escape')hide();if(e.key==='ArrowLeft')show(i-1);if(e.key==='ArrowRight')show(i+1);});
})();
