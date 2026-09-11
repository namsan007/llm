const canvas = document.querySelector('#game-canvas');
const ctx = canvas.getContext('2d');
const overlay = document.querySelector('#overlay');
const overlayTitle = document.querySelector('#overlay-title');
const overlayCopy = document.querySelector('#overlay-copy');
const startButton = document.querySelector('#start-button');
const pauseButton = document.querySelector('#pause-button');
const restartButton = document.querySelector('#restart-button');
const scoreElement = document.querySelector('#score');
const highScoreElement = document.querySelector('#high-score');
const stageElement = document.querySelector('#stage');
const armorText = document.querySelector('#armor-text');
const armorBar = document.querySelector('#armor-bar');
const weaponElement = document.querySelector('#weapon');
const logElement = document.querySelector('#log');
const missionStatus = document.querySelector('#mission-status');

const W = canvas.width;
const H = canvas.height;
const keys = new Set();
const game = { playing:false, paused:false, score:0, highScore:Number(localStorage.getItem('sky-raiders-high-score')) || 0, stage:1, armor:100, frame:0, spawnTimer:0, cannonTimer:130, boss:null, alert:0, shake:0, lastTime:0 };
const player = { x:W / 2, y:H - 90, speed:4.6, cooldown:0, power:1, shield:0, invulnerable:0 };
let bullets = [];
let enemyBullets = [];
let enemies = [];
let cannons = [];
let particles = [];
let powerups = [];
let stars = Array.from({ length:70 }, (_, index) => ({ x:(index * 73) % W, y:(index * 47) % H, speed:0.3 + (index % 4) * 0.18, size:1 + index % 2 }));

function formatScore(value) { return String(value).padStart(7, '0'); }
function setLog(message) { logElement.textContent = message; }
function updateHud() { scoreElement.textContent = formatScore(game.score); highScoreElement.textContent = formatScore(game.highScore); stageElement.textContent = String(game.stage).padStart(2, '0'); armorText.textContent = `${Math.max(0, Math.ceil(game.armor))}%`; armorBar.style.width = `${Math.max(0, game.armor)}%`; armorBar.style.background = game.armor < 35 ? 'var(--red)' : 'var(--cyan)'; weaponElement.textContent = `VULCAN // LV.${player.power}`; }
function random(min, max) { return Math.random() * (max - min) + min; }
function addBurst(x, y, color, amount = 10) { for (let i = 0; i < amount; i += 1) particles.push({ x, y, vx:random(-2.5,2.5), vy:random(-2.5,2.5), life:random(18,38), color, size:random(1,3) }); }
function spawnEnemy(type = Math.random() < 0.78 ? 'scout' : 'zigzag') { const size = type === 'scout' ? 15 : 18; enemies.push({ type, x:random(28,W-28), y:-35, size, hp:type === 'scout' ? 1 : 2, maxHp:type === 'scout' ? 1 : 2, speed:random(1.1,1.8) + game.stage*.08, phase:random(0,Math.PI*2), fire:random(70,170), color:type === 'scout' ? '#ff5e67' : '#ffb14e' }); }
function spawnCannon() { cannons.push({ x:random(34,W-34), y:-34, hp:4, maxHp:4, speed:random(.45,.8), fire:random(80,150), phase:random(0,Math.PI*2) }); }
function spawnBoss() { game.boss = { x:W/2, y:-90, targetY:105, hp:45 + game.stage * 14, maxHp:45 + game.stage * 14, fire:55, phase:0 }; game.alert=170; game.shake=4; setLog('WARNING: 대형 폭격기 편대 출현!'); }
function resetGame() { game.score=0; game.stage=1; game.armor=100; game.frame=0; game.spawnTimer=0; game.cannonTimer=130; game.boss=null; game.alert=0; game.shake=0; bullets=[]; enemyBullets=[]; enemies=[]; cannons=[]; particles=[]; powerups=[]; player.x=W/2; player.y=H-90; player.power=1; player.shield=0; player.cooldown=0; player.invulnerable=0; updateHud(); }
function startGame() { resetGame(); game.playing=true; game.paused=false; overlay.classList.add('hidden'); pauseButton.disabled=false; pauseButton.textContent='Ⅱ 일시정지'; missionStatus.textContent='ACTIVE'; setLog('적 편대가 접근 중입니다.'); game.lastTime=performance.now(); requestAnimationFrame(loop); }
function endGame() { game.playing=false; game.paused=false; pauseButton.disabled=true; missionStatus.textContent='FAILED'; if (game.score > game.highScore) { game.highScore=game.score; localStorage.setItem('sky-raiders-high-score', game.highScore); } updateHud(); overlayTitle.textContent='MISSION FAILED'; overlayCopy.textContent=`최종 점수 ${formatScore(game.score)} · 다시 하늘로 출격하세요.`; startButton.innerHTML='재출격 <span>→</span>'; overlay.classList.remove('hidden'); }
function togglePause() { if (!game.playing) return; game.paused=!game.paused; pauseButton.textContent=game.paused?'▶ 계속하기':'Ⅱ 일시정지'; missionStatus.textContent=game.paused?'PAUSED':'ACTIVE'; if (game.paused) { overlayTitle.textContent='PAUSED'; overlayCopy.textContent='잠시 숨을 고르고 다시 출격하세요.'; startButton.textContent='계속하기'; overlay.classList.remove('hidden'); } else { overlay.classList.add('hidden'); game.lastTime=performance.now(); requestAnimationFrame(loop); } }
function fire() { if (player.cooldown > 0) return; const spread = player.power >= 3 ? [-0.18,0,0.18] : player.power === 2 ? [-0.1,0.1] : [0]; spread.forEach(angle => bullets.push({ x:player.x, y:player.y-23, vx:Math.sin(angle)*3, vy:-8.5, damage:1 })); player.cooldown=player.power >= 3 ? 7 : player.power === 2 ? 9 : 12; }
function hitPlayer(damage=16) { if (player.invulnerable > 0) return; if (player.shield > 0) { player.shield=0; player.invulnerable=45; game.alert=18; addBurst(player.x,player.y,'#4fe0dc',20); setLog('실드가 공격을 막았습니다.'); return; } game.armor-=damage; player.invulnerable=70; game.alert=22; game.shake=8; addBurst(player.x,player.y,'#70a5ff',18); setLog('피격! 장갑 손상 감지.'); updateHud(); if (game.armor<=0) endGame(); }
function circleHit(a,b,radius) { return Math.hypot(a.x-b.x,a.y-b.y)<radius; }
function update(dt) {
  game.frame+=1; player.cooldown=Math.max(0,player.cooldown-dt); player.invulnerable=Math.max(0,player.invulnerable-dt); player.shield=Math.max(0,player.shield-dt); game.alert=Math.max(0,game.alert-dt); game.shake=Math.max(0,game.shake-dt);
  const moveX=(keys.has('left')||keys.has('a')?-1:0)+(keys.has('right')||keys.has('d')?1:0); const moveY=(keys.has('up')||keys.has('w')?-1:0)+(keys.has('down')||keys.has('s')?1:0); player.x=Math.max(22,Math.min(W-22,player.x+moveX*player.speed*dt)); player.y=Math.max(50,Math.min(H-35,player.y+moveY*player.speed*dt)); if (keys.has('fire')||keys.has(' ')) fire();
  stars.forEach(star=>{ star.y+=star.speed*dt*(1+game.stage*.08); if(star.y>H) star.y=-3; });
  game.spawnTimer-=dt; if(!game.boss && game.spawnTimer<=0){ spawnEnemy(); game.spawnTimer=Math.max(22,60-game.stage*3); if(game.frame>0 && game.frame%(60*25)===0) spawnBoss(); }
  game.cannonTimer-=dt; if(!game.boss && game.cannonTimer<=0){ spawnCannon(); game.cannonTimer=random(150,270); }
  bullets.forEach(b=>{b.x+=b.vx*dt;b.y+=b.vy*dt;}); bullets=bullets.filter(b=>b.y>-20);
  enemies.forEach(enemy=>{ enemy.y+=enemy.speed*dt; enemy.phase+=.035*dt; if(enemy.type==='zigzag') enemy.x+=Math.sin(enemy.phase)*1.8*dt; enemy.fire-=dt; if(enemy.fire<=0){enemyBullets.push({x:enemy.x,y:enemy.y+15,vx:0,vy:random(2.1,3.3),size:4});enemy.fire=random(90,180);} if(enemy.y>H+30) enemy.dead=true; });
  cannons.forEach(cannon=>{ cannon.y+=cannon.speed*dt; cannon.phase+=.025*dt; cannon.fire-=dt; if(cannon.fire<=0){const angle=Math.atan2(player.y-cannon.y,player.x-cannon.x);enemyBullets.push({x:cannon.x,y:cannon.y-12,vx:Math.cos(angle)*2.6,vy:Math.sin(angle)*2.6,size:6, cannon:true});cannon.fire=random(95,175);} if(cannon.y>H+45)cannon.dead=true; });
  enemyBullets.forEach(b=>{b.x+=b.vx*dt;b.y+=b.vy*dt;if(circleHit(b,player,14)){b.dead=true;hitPlayer(10);}}); enemyBullets=enemyBullets.filter(b=>!b.dead&&b.y<H+20);
  enemies.forEach(enemy=>{ bullets.forEach(b=>{if(!b.dead&&!enemy.dead&&circleHit(b,enemy,enemy.size+4)){b.dead=true;enemy.hp-=b.damage;addBurst(b.x,b.y,'#ffd45c',3);if(enemy.hp<=0){enemy.dead=true;game.score+=enemy.type==='scout'?100:250;addBurst(enemy.x,enemy.y,enemy.color,14);if(Math.random()<.16)powerups.push({x:enemy.x,y:enemy.y,type:['power','repair','shield','bomb'][Math.floor(Math.random()*4)]});}}}); if(!enemy.dead&&circleHit(enemy,player,21)){enemy.dead=true;hitPlayer(22);} }); enemies=enemies.filter(enemy=>!enemy.dead&&enemy.y<H+35);
  cannons.forEach(cannon=>{ bullets.forEach(b=>{if(!b.dead&&!cannon.dead&&circleHit(b,cannon,19)){b.dead=true;cannon.hp-=b.damage;addBurst(b.x,b.y,'#ffd45c',3);if(cannon.hp<=0){cannon.dead=true;game.score+=350;addBurst(cannon.x,cannon.y,'#ffb84d',18);if(Math.random()<.45)powerups.push({x:cannon.x,y:cannon.y,type:['repair','shield','bomb'][Math.floor(Math.random()*3)]});}}}); if(!cannon.dead&&circleHit(cannon,player,22)){cannon.dead=true;hitPlayer(26);} }); cannons=cannons.filter(cannon=>!cannon.dead&&cannon.y<H+45);
  if(game.boss){ const boss=game.boss; boss.phase+=.025*dt; boss.y=Math.min(boss.targetY,boss.y+1.2*dt); boss.x=W/2+Math.sin(boss.phase)*115; boss.fire-=dt; if(boss.fire<=0){for(let i=-2;i<=2;i+=1)enemyBullets.push({x:boss.x,y:boss.y+26,vx:i*.55,vy:2.5,size:5});boss.fire=70;} bullets.forEach(b=>{if(!b.dead&&circleHit(b,boss,38)){b.dead=true;boss.hp-=b.damage;addBurst(b.x,b.y,'#ffd45c',2);}}); if(boss.hp<=0){game.score+=3000;game.stage+=1;addBurst(boss.x,boss.y,'#ffb14e',45);powerups.push({x:boss.x,y:boss.y,type:'power'});game.boss=null;setLog('보스 격추! 다음 스테이지로 진입합니다.');updateHud();} }
  powerups.forEach(item=>{item.y+=1.4*dt;if(circleHit(item,player,24)){item.dead=true;if(item.type==='power'){player.power=Math.min(3,player.power+1);setLog('무장 강화! VULCAN 출력 상승.');}else if(item.type==='repair'){game.armor=Math.min(100,game.armor+25);setLog('수리 파츠 획득. 장갑 +25%.');}else if(item.type==='shield'){player.shield=420;setLog('에너지 실드 전개. 다음 피격을 방어합니다.');}else{enemyBullets=[];enemies.forEach(enemy=>{enemy.hp-=3;if(enemy.hp<=0)enemy.dead=true;});cannons.forEach(cannon=>{cannon.hp-=3;if(cannon.hp<=0)cannon.dead=true;});game.score+=500;addBurst(player.x,player.y,'#4fe0dc',30);setLog('EMP 폭탄 발동! 적 탄막이 소거됐습니다.');}updateHud();}});powerups=powerups.filter(item=>!item.dead&&item.y<H+20);
  particles.forEach(p=>{p.x+=p.vx*dt;p.y+=p.vy*dt;p.life-=dt;});particles=particles.filter(p=>p.life>0); if(game.frame%15===0)updateHud();
}
function draw() { ctx.save(); if(game.shake>0)ctx.translate(random(-game.shake,game.shake),random(-game.shake,game.shake)); ctx.fillStyle='#06141e';ctx.fillRect(0,0,W,H); ctx.fillStyle='#d5f7f0';stars.forEach(star=>{ctx.globalAlpha=.25+star.size*.15;ctx.fillRect(star.x,star.y,star.size,star.size*2);});ctx.globalAlpha=1;
  ctx.strokeStyle='#1a3a49';ctx.lineWidth=1;for(let y=(game.frame*.6)%48-48;y<H;y+=48){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
  const groundScroll=(game.frame*1.1)%160;ctx.fillStyle='#0a2630';ctx.beginPath();ctx.moveTo(0,95);ctx.lineTo(48,45);ctx.lineTo(94,88);ctx.lineTo(148,32);ctx.lineTo(202,82);ctx.lineTo(260,38);ctx.lineTo(320,88);ctx.lineTo(370,48);ctx.lineTo(W,78);ctx.lineTo(W,160);ctx.lineTo(0,160);ctx.closePath();ctx.fill();
  ctx.globalAlpha=.16;for(let smokeIndex=0;smokeIndex<5;smokeIndex+=1){const smokeX=42+smokeIndex*86+Math.sin(game.frame*.01+smokeIndex)*12;const smokeY=135+((game.frame*(.22+smokeIndex*.03)+smokeIndex*91)%420);ctx.fillStyle=smokeIndex%2?'#53656a':'#243f48';ctx.beginPath();ctx.arc(smokeX,smokeY,18+smokeIndex*3,0,Math.PI*2);ctx.arc(smokeX+13,smokeY-15,13+smokeIndex*2,0,Math.PI*2);ctx.arc(smokeX-12,smokeY-9,15,0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;
  for(let y=groundScroll-160;y<H+160;y+=160){ctx.fillStyle='#0b3038';ctx.fillRect(0,y+112,W,45);ctx.fillStyle='#123b42';ctx.fillRect(0,y+116,W,2);ctx.fillRect(0,y+151,W,2);ctx.fillStyle='#17606a';ctx.fillRect(34,y+128,104,3);ctx.fillRect(278,y+128,108,3);ctx.fillStyle='#09232d';ctx.fillRect(18,y+120,34,20);ctx.fillRect(367,y+120,36,20);
    ctx.save();ctx.translate(75,y+108);ctx.fillStyle='#172f38';ctx.fillRect(-18,10,36,18);ctx.fillStyle='#415b5e';ctx.fillRect(-15,7,30,7);ctx.fillStyle='#263f45';ctx.beginPath();ctx.arc(0,5,14,Math.PI,Math.PI*2);ctx.fill();ctx.fillStyle='#ffb84d';ctx.fillRect(-3,-10,6,18);ctx.fillStyle='#ff5e67';ctx.fillRect(-1,-8,2,13);ctx.restore();
    ctx.save();ctx.translate(W-76,y+112);ctx.fillStyle='#132c35';ctx.fillRect(-25,7,50,22);ctx.fillStyle='#426067';ctx.fillRect(-20,3,40,7);ctx.fillStyle='#253e44';ctx.beginPath();ctx.arc(0,4,16,Math.PI,Math.PI*2);ctx.fill();ctx.fillStyle='#ffb84d';ctx.fillRect(-3,-12,6,19);ctx.restore();
  }
  powerups.forEach(item=>{const itemColor={power:'#ffd45c',repair:'#4fe0dc',shield:'#70a5ff',bomb:'#ff7b8a'}[item.type];const itemSymbol={power:'P',repair:'+',shield:'S',bomb:'E'}[item.type];ctx.fillStyle=itemColor;ctx.shadowColor=itemColor;ctx.shadowBlur=12;ctx.beginPath();ctx.arc(item.x,item.y,11,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle='#07131b';ctx.font='bold 13px Share Tech Mono';ctx.textAlign='center';ctx.fillText(itemSymbol,item.x,item.y+5);});
  bullets.forEach(b=>{ctx.fillStyle='#fff4ad';ctx.shadowColor='#ffd45c';ctx.shadowBlur=12;ctx.fillRect(b.x-2,b.y-9,4,12);ctx.shadowBlur=0;}); enemyBullets.forEach(b=>{ctx.fillStyle='#ff6570';ctx.beginPath();ctx.arc(b.x,b.y,b.size,0,Math.PI*2);ctx.fill();});
  cannons.forEach(cannon=>{ctx.save();ctx.translate(cannon.x,cannon.y);ctx.fillStyle='#263f45';ctx.fillRect(-18,4,36,18);ctx.fillStyle='#4c6b6c';ctx.beginPath();ctx.arc(0,5,15,Math.PI,Math.PI*2);ctx.fill();ctx.rotate(Math.atan2(player.y-cannon.y,player.x-cannon.x)+Math.PI/2);ctx.fillStyle='#172a31';ctx.fillRect(-4,-23,8,25);ctx.fillStyle='#ffb84d';ctx.fillRect(-2,-23,4,7);ctx.restore();ctx.fillStyle='#281d2b';ctx.fillRect(cannon.x-18,cannon.y-29,36,3);ctx.fillStyle='#ff5e67';ctx.fillRect(cannon.x-18,cannon.y-29,36*cannon.hp/cannon.maxHp,3);});
  enemies.forEach(enemy=>{ctx.save();ctx.translate(enemy.x,enemy.y);ctx.shadowColor=enemy.color;ctx.shadowBlur=9;ctx.fillStyle=enemy.color;
    if(enemy.type==='scout'){ctx.beginPath();ctx.moveTo(0,enemy.size+10);ctx.lineTo(-7,5);ctx.lineTo(-29,-7);ctx.lineTo(-22,-13);ctx.lineTo(-6,-10);ctx.lineTo(0,-18);ctx.lineTo(6,-10);ctx.lineTo(22,-13);ctx.lineTo(29,-7);ctx.lineTo(7,5);ctx.closePath();ctx.fill();ctx.fillStyle='#ffe9bd';ctx.fillRect(-4,-7,8,7);ctx.fillStyle='#332c86';ctx.fillRect(-21,-8,9,3);ctx.fillRect(12,-8,9,3);}
    else{ctx.beginPath();ctx.moveTo(0,enemy.size+12);ctx.lineTo(-13,10);ctx.lineTo(-35,-4);ctx.lineTo(-30,-14);ctx.lineTo(-10,-11);ctx.lineTo(0,-18);ctx.lineTo(10,-11);ctx.lineTo(30,-14);ctx.lineTo(35,-4);ctx.lineTo(13,10);ctx.closePath();ctx.fill();ctx.fillStyle='#ffe9bd';ctx.fillRect(-6,-7,12,8);ctx.fillStyle='#6b2e4b';ctx.fillRect(-28,-6,12,4);ctx.fillRect(16,-6,12,4);ctx.fillStyle='#ff5e67';ctx.fillRect(-3,9,6,5);}
    ctx.shadowBlur=0;ctx.restore();});
  if(game.boss){const boss=game.boss;ctx.save();ctx.translate(boss.x,boss.y);ctx.fillStyle='#b34d62';ctx.beginPath();ctx.moveTo(0,-35);ctx.lineTo(42,22);ctx.lineTo(19,28);ctx.lineTo(0,15);ctx.lineTo(-19,28);ctx.lineTo(-42,22);ctx.closePath();ctx.fill();ctx.fillStyle='#ffd45c';ctx.fillRect(-6,-13,12,7);ctx.restore();ctx.fillStyle='#39202b';ctx.fillRect(45,24,W-90,6);ctx.fillStyle='#ff5e67';ctx.fillRect(45,24,(W-90)*boss.hp/boss.maxHp,6);}
  if(player.invulnerable%8<4){ctx.save();ctx.translate(player.x,player.y);if(player.shield>0){ctx.strokeStyle='#70a5ff';ctx.lineWidth=2;ctx.shadowColor='#70a5ff';ctx.shadowBlur=18;ctx.beginPath();ctx.arc(0,2,38+Math.sin(game.frame*.12)*2,0,Math.PI*2);ctx.stroke();ctx.shadowBlur=0;}ctx.shadowColor='#4fe0dc';ctx.shadowBlur=14;
    ctx.fillStyle='#ffb84d';ctx.beginPath();ctx.moveTo(-13,20);ctx.lineTo(-8,36);ctx.lineTo(-3,21);ctx.closePath();ctx.fill();ctx.beginPath();ctx.moveTo(13,20);ctx.lineTo(8,36);ctx.lineTo(3,21);ctx.closePath();ctx.fill();ctx.shadowBlur=0;
    ctx.fillStyle='#263fbd';ctx.beginPath();ctx.moveTo(0,-31);ctx.lineTo(6,-15);ctx.lineTo(29,12);ctx.lineTo(20,18);ctx.lineTo(7,13);ctx.lineTo(0,23);ctx.lineTo(-7,13);ctx.lineTo(-20,18);ctx.lineTo(-29,12);ctx.lineTo(-6,-15);ctx.closePath();ctx.fill();
    ctx.strokeStyle='#70a5ff';ctx.lineWidth=1.5;ctx.stroke();
    ctx.fillStyle='#4fe0dc';ctx.beginPath();ctx.moveTo(0,-29);ctx.lineTo(5,-11);ctx.lineTo(4,16);ctx.lineTo(0,23);ctx.lineTo(-4,16);ctx.lineTo(-5,-11);ctx.closePath();ctx.fill();
    ctx.fillStyle='#e9f5f1';ctx.beginPath();ctx.moveTo(0,-23);ctx.lineTo(4,-10);ctx.lineTo(3,9);ctx.lineTo(0,14);ctx.lineTo(-3,9);ctx.lineTo(-4,-10);ctx.closePath();ctx.fill();
    ctx.fillStyle='#16277f';ctx.beginPath();ctx.moveTo(-4,-12);ctx.lineTo(0,-19);ctx.lineTo(4,-12);ctx.lineTo(3,-4);ctx.lineTo(-3,-4);ctx.closePath();ctx.fill();
    ctx.fillStyle='#ff5e67';ctx.fillRect(-23,12,8,3);ctx.fillRect(15,12,8,3);ctx.fillStyle='#ffd45c';ctx.fillRect(-2,-26,4,5);ctx.restore();}
  particles.forEach(p=>{ctx.globalAlpha=Math.max(0,p.life/38);ctx.fillStyle=p.color;ctx.fillRect(p.x,p.y,p.size,p.size);});ctx.globalAlpha=1;
  if(game.alert>0){const alertStrength=Math.min(.24,game.alert/420);ctx.fillStyle=`rgba(190,24,38,${alertStrength})`;ctx.fillRect(0,0,W,H);ctx.strokeStyle=`rgba(255,80,80,${Math.min(.85,game.alert/110)})`;ctx.lineWidth=3;ctx.strokeRect(7,7,W-14,H-14);if(game.boss&&game.alert>70){ctx.fillStyle='#ff5e67';ctx.font='700 18px Barlow Condensed';ctx.textAlign='center';ctx.fillText('!! AIR RAID WARNING !!',W/2,48);ctx.font='11px Share Tech Mono';ctx.fillStyle='#ffd45c';ctx.fillText('HEAVY BOMBER INBOUND',W/2,66);}}
  ctx.restore(); }
function loop(time){if(!game.playing||game.paused)return;const dt=Math.min(2,(time-game.lastTime)/16.67||1);game.lastTime=time;update(dt);draw();requestAnimationFrame(loop);}
function setKey(key,value){if(value)keys.add(key);else keys.delete(key);}
const keyMap={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down',' ':'fire',a:'a',d:'d',w:'w',s:'s'};
document.addEventListener('keydown',event=>{const key=keyMap[event.key];if(key){event.preventDefault();setKey(key,true);}if(event.key.toLowerCase()==='p')togglePause();});document.addEventListener('keyup',event=>{const key=keyMap[event.key];if(key){event.preventDefault();setKey(key,false);}});
document.querySelectorAll('[data-key]').forEach(button=>{const key=button.dataset.key;button.addEventListener('pointerdown',event=>{event.preventDefault();setKey(key,true);button.setPointerCapture(event.pointerId);});button.addEventListener('pointerup',()=>setKey(key,false));button.addEventListener('pointercancel',()=>setKey(key,false));});
startButton.addEventListener('click',()=>game.paused?togglePause():startGame());pauseButton.addEventListener('click',togglePause);restartButton.addEventListener('click',startGame);updateHud();draw();
