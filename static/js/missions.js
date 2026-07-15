document.addEventListener('DOMContentLoaded', async () => {
  const list = document.querySelector('#listaMisiones');
  const counter = document.querySelector('#numeroCompletadas');
  const finalMessage = document.querySelector('#mensajeFinal');
  const greeting = document.querySelector('#saludo');

  let missions = [];

  try {
    const response = await fetch('/api/misiones');
    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(result.error || 'No se pudieron recuperar tus misiones.');
    }

    missions = result.missions;
    if (result.guest?.nombre) {
      greeting.textContent = `La aventura continúa, ${result.guest.nombre}`;
    }

    missions.forEach((mission, index) => list.appendChild(card(mission, index)));
    progress();
  } catch (error) {
    list.innerHTML = `<p class="estado error">${error.message} <a href="/">Volver al inicio</a></p>`;
  }

  function progress() {
    const completed = missions.filter(mission => mission.completed).length;
    counter.textContent = `${completed}/3`;
    finalMessage.classList.toggle('visible', completed === 3);
  }

  function card(mission, index) {
    const id = `recuerdo-${mission.id}`;
    const element = document.createElement('article');
    element.className = `mision${mission.completed ? ' completada' : ''}`;

    element.innerHTML = `
      <div class="cabecera-mision">
        <span class="numero">${mission.completed ? '✓' : index + 1}</span>
        <div class="texto-mision">
          <h3>${escapeHtml(mission.text)}</h3>
          <p>Elige una fotografía o un vídeo corto.</p>
        </div>
      </div>
      <div class="zona-recuerdo">
        <input id="${id}" class="input-archivo" type="file" accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime">
        <label class="boton-recuerdo" for="${id}">${mission.completed ? '✓ Cambiar recuerdo' : '📷 Elegir recuerdo'}</label>
        <p class="estado${mission.completed ? ' completado' : ''}">${mission.completed ? '✓ Misión completada' : 'Esperando tu recuerdo.'}</p>
        <div class="marco-recuerdo${mission.media_url ? ' visible' : ''}">
          <img class="vista-imagen${mission.media_url && mission.media_type?.startsWith('image/') ? ' visible' : ''}" alt="Vista previa del recuerdo" ${mission.media_url && mission.media_type?.startsWith('image/') ? `src="${mission.media_url}"` : ''}>
          <video class="vista-video${mission.media_url && mission.media_type?.startsWith('video/') ? ' visible' : ''}" controls playsinline ${mission.media_url && mission.media_type?.startsWith('video/') ? `src="${mission.media_url}"` : ''}></video>
          <p class="pie-foto">Un recuerdo para Madro &amp; David</p>
        </div>
      </div>`;

    const input = element.querySelector('input');
    input.addEventListener('change', async (event) => {
      const file = event.target.files[0];
      if (!file) return;

      const button = element.querySelector('.boton-recuerdo');
      const status = element.querySelector('.estado');
      button.classList.add('bloqueado');
      status.className = 'estado subiendo';
      status.textContent = 'Subiendo recuerdo…';

      try {
        showPreview(element, file);
        const formData = new FormData();
        formData.append('archivo', file);
        formData.append('mission_id', mission.id);

        const response = await fetch('/api/misiones/subir', {
          method: 'POST',
          body: formData
        });
        const result = await response.json();

        if (!response.ok || !result.ok) {
          throw new Error(result.error || 'No se pudo subir el recuerdo.');
        }

        mission.completed = true;
        mission.media_url = result.url;
        mission.media_type = result.content_type;
        element.classList.add('completada');
        element.querySelector('.numero').textContent = '✓';
        button.textContent = '✓ Cambiar recuerdo';
        status.className = 'estado completado';
        status.textContent = '✓ Recuerdo subido. Misión completada';
        progress();
      } catch (error) {
        status.className = 'estado error';
        status.textContent = error.message;
      } finally {
        button.classList.remove('bloqueado');
      }
    });

    return element;
  }

  function showPreview(element, file) {
    const image = element.querySelector('.vista-imagen');
    const video = element.querySelector('.vista-video');
    const frame = element.querySelector('.marco-recuerdo');
    const url = URL.createObjectURL(file);

    image.classList.remove('visible');
    video.classList.remove('visible');

    if (file.type.startsWith('video/')) {
      video.src = url;
      video.classList.add('visible');
      video.onloadeddata = () => URL.revokeObjectURL(url);
    } else {
      image.src = url;
      image.classList.add('visible');
      image.onload = () => URL.revokeObjectURL(url);
    }

    frame.classList.add('visible');
  }

  function escapeHtml(value) {
    const container = document.createElement('div');
    container.textContent = value;
    return container.innerHTML;
  }
});
