document.addEventListener('DOMContentLoaded', () => {
  const pool = ['Hazte una foto con los novios.', 'Sube una foto del brindis.', 'Haz una foto con un grupo de 5 personas.', 'Sube una foto bailando.', 'Hazte una foto con tu persona especial.', 'Sube una foto del atardecer.', 'Pilla a los novios bailando.', 'Sube una foto haciendo el tonto.', 'Haz una foto de la ceremonia.'];
  const assignmentKey = 'boda-madro-david-misiones';
  const completedKey = 'boda-madro-david-completadas';
  const list = document.querySelector('#listaMisiones');
  const counter = document.querySelector('#numeroCompletadas');
  const finalMessage = document.querySelector('#mensajeFinal');
  const guest = JSON.parse(localStorage.getItem('boda-madro-david-invitado') || '{}');
  const saved = JSON.parse(localStorage.getItem(assignmentKey) || 'null');
  const missions = Array.isArray(saved) && saved.length === 3 ? saved : [...pool].sort(() => Math.random() - .5).slice(0, 3);
  const completed = new Set(JSON.parse(localStorage.getItem(completedKey) || '[]'));
  localStorage.setItem(assignmentKey, JSON.stringify(missions));
  if (guest.nombre) document.querySelector('#saludo').textContent = `La aventura continúa, ${guest.nombre}`;

  function progress() { counter.textContent = `${completed.size}/3`; finalMessage.classList.toggle('visible', completed.size === 3); localStorage.setItem(completedKey, JSON.stringify([...completed])); }
  function card(text, index) {
    const done = completed.has(index); const id = `recuerdo-${index}`; const element = document.createElement('div');
    element.className = `mision${done ? ' completada' : ''}`;
    element.innerHTML = `<div class="cabecera-mision"><span class="numero">${done ? '✓' : index + 1}</span><div class="texto-mision"><h3>${text}</h3><p>Elige una fotografía o un vídeo corto.</p></div></div><div class="zona-recuerdo"><input id="${id}" class="input-archivo" type="file" accept="image/*,video/mp4,video/quicktime"><label class="boton-recuerdo" for="${id}">${done ? '✓ Cambiar recuerdo' : '📷 Elegir recuerdo'}</label><p class="estado${done ? ' completado' : ''}">${done ? '✓ Misión completada' : 'Esperando tu recuerdo.'}</p><div class="marco-recuerdo"><img class="vista-imagen" alt="Vista previa del recuerdo"><video class="vista-video" controls playsinline></video><p class="pie-foto">Un recuerdo para Madro &amp; David</p></div></div>`;
    element.querySelector('input').addEventListener('change', event => { const file = event.target.files[0]; if (!file) return; const image = element.querySelector('.vista-imagen'); const video = element.querySelector('.vista-video'); const url = URL.createObjectURL(file); image.classList.remove('visible'); video.classList.remove('visible'); if (file.type.startsWith('video/')) { video.src = url; video.classList.add('visible'); } else { image.src = url; image.classList.add('visible'); } element.querySelector('.marco-recuerdo').classList.add('visible'); element.classList.add('completada'); completed.add(index); element.querySelector('.numero').textContent = '✓'; element.querySelector('.boton-recuerdo').textContent = '✓ Cambiar recuerdo'; const status = element.querySelector('.estado'); status.className = 'estado completado'; status.textContent = '✓ Misión completada'; progress(); });
    return element;
  }
  missions.forEach((mission, index) => list.appendChild(card(mission, index))); progress();
});
