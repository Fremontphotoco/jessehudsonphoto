
(function(){
var t=document.querySelector('.theme');try{var saved=localStorage.getItem('theme');if(saved)document.documentElement.setAttribute('data-theme',saved);}catch(e){}
if(t){t.addEventListener('click',function(){var cur=document.documentElement.getAttribute('data-theme');var dark=cur?cur==='dark':matchMedia('(prefers-color-scheme:dark)').matches;var next=dark?'light':'dark';document.documentElement.setAttribute('data-theme',next);try{localStorage.setItem('theme',next)}catch(e){}});}
/* showcase */
var imgs=[].slice.call(document.querySelectorAll('.stage img')),steps=[].slice.call(document.querySelectorAll('.step')),items=[].slice.call(document.querySelectorAll('.list li')),cnt=document.querySelector('.count');
function go(n){imgs.forEach(function(im,k){im.classList.toggle('on',k===n);});items.forEach(function(li,k){li.classList.toggle('on',k===n);});if(cnt)cnt.textContent=(n+1)+' / '+imgs.length;[n,n+1,n+2,n-1].forEach(function(j){var nx=imgs[j];if(nx&&nx.dataset.src){nx.src=nx.dataset.src;delete nx.dataset.src;}});}
if(steps.length){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)go(+e.target.dataset.i);});},{threshold:.5});steps.forEach(function(s){io.observe(s);});go(0);
items.forEach(function(li,k){var a=li.querySelector('a');if(a&&a.getAttribute('href')==='#')a.addEventListener('click',function(e){e.preventDefault();steps[k].scrollIntoView({behavior:'smooth'});});});var cur=0,lock=0;function jump(d){var n=Math.min(Math.max(cur+d,0),steps.length-1);if(n===cur)return;cur=n;steps[n].scrollIntoView({behavior:'smooth'});}var io2=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)cur=+e.target.dataset.i;});},{threshold:.5});steps.forEach(function(st){io2.observe(st);});document.addEventListener('keydown',function(e){if(document.getElementById('lb')&&document.getElementById('lb').classList.contains('on'))return;if(e.key==='ArrowRight'||e.key==='ArrowDown'||e.key==='PageDown'||e.key===' '){e.preventDefault();jump(1);}else if(e.key==='ArrowLeft'||e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();jump(-1);}else if(e.key==='Home'){jump(-cur);}else if(e.key==='End'){jump(steps.length);}});window.addEventListener('wheel',function(e){if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)||Math.abs(e.deltaX)<25)return;e.preventDefault();var now=Date.now();if(now-lock<700)return;lock=now;jump(e.deltaX>0?1:-1);},{passive:false});var tx=null;window.addEventListener('touchstart',function(e){tx=e.touches[0].clientX;},{passive:true});window.addEventListener('touchend',function(e){if(tx===null)return;var dx=e.changedTouches[0].clientX-tx;tx=null;if(Math.abs(dx)>60)jump(dx<0?1:-1);},{passive:true});}
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
