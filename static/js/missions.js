document.addEventListener('DOMContentLoaded', async () => {
  const MISSION_TOTAL = 5;
  const MAX_DIMENSION = 2200;
  const TARGET_BYTES = 800 * 1024;
  const MAX_BYTES = 1024 * 1024;
  const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
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
    list.innerHTML = `<p class="estado error">${escapeHtml(error.message)} <a href="/">Volver al inicio</a></p>`;
  }

  function progress() {
    const completed = missions.filter(mission => mission.completed).length;
    counter.textContent = `${completed}/${MISSION_TOTAL}`;
    finalMessage.classList.toggle('visible', completed === MISSION_TOTAL);
  }

  function card(mission, index) {
    const id = `recuerdo-${mission.id}`;
    const element = document.createElement('article');
    const hasImage = mission.media_url && mission.media_type?.startsWith('image/');
    element.className = `mision${mission.completed ? ' completada' : ''}`;

    element.innerHTML = `
      <div class="cabecera-mision">
        <span class="numero">${mission.completed ? '✓' : index + 1}</span>
        <div class="texto-mision">
          <h3>${escapeHtml(mission.text)}</h3>
          <p>Elige una fotografía en formato JPG, PNG o WebP.</p>
        </div>
      </div>
      <div class="zona-recuerdo">
        <input id="${id}" class="input-archivo" type="file" accept="image/jpeg,image/png,image/webp">
        <label class="boton-recuerdo" for="${id}">${mission.completed ? '✓ Cambiar recuerdo' : '📷 Elegir recuerdo'}</label>
        <p class="estado${mission.completed ? ' completado' : ''}">${mission.completed ? '✓ Misión completada' : 'Esperando tu recuerdo.'}</p>
        <div class="marco-recuerdo${hasImage ? ' visible' : ''}">
          <img class="vista-imagen${hasImage ? ' visible' : ''}" alt="Vista previa del recuerdo" ${hasImage ? `src="${mission.media_url}"` : ''}>
          <p class="pie-foto">Un recuerdo para David &amp; Madro</p>
        </div>
      </div>`;

    const input = element.querySelector('input');
    input.addEventListener('change', async (event) => {
      const original = event.target.files[0];
      if (!original) return;

      const button = element.querySelector('.boton-recuerdo');
      const status = element.querySelector('.estado');
      button.classList.add('bloqueado');
      status.className = 'estado subiendo';
      status.textContent = 'Preparando fotografía…';

      try {
        if (!ACCEPTED_TYPES.has(original.type)) {
          throw new Error('Solo se admiten fotografías JPG, PNG o WebP.');
        }

        const photo = await compressPhoto(original);
        showPreview(element, photo);
        status.textContent = `Subiendo fotografía (${formatBytes(photo.size)})…`;

        const formData = new FormData();
        formData.append('archivo', photo, `mision-${mission.id}.jpg`);
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
        input.value = '';
        button.classList.remove('bloqueado');
      }
    });

    return element;
  }

  async function compressPhoto(file) {
    if (file.type === 'image/jpeg' && file.size <= MAX_BYTES) {
      return file;
    }

    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext('2d', { alpha: false });
    context.fillStyle = '#fff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();

    const sizeLimit = file.size < MAX_BYTES ? file.size : MAX_BYTES;
    const preferredSize = Math.min(TARGET_BYTES, sizeLimit);
    let lowerQuality = .42;
    let upperQuality = .92;
    let best = await canvasToBlob(canvas, lowerQuality);

    for (let attempt = 0; attempt < 7; attempt += 1) {
      const quality = (lowerQuality + upperQuality) / 2;
      const candidate = await canvasToBlob(canvas, quality);

      if (candidate.size <= sizeLimit) {
        best = candidate;
        if (candidate.size < preferredSize) lowerQuality = quality;
        else upperQuality = quality;
      } else {
        upperQuality = quality;
      }
    }

    while (best.size > sizeLimit && canvas.width > 320 && canvas.height > 320) {
      const previous = document.createElement('canvas');
      previous.width = canvas.width;
      previous.height = canvas.height;
      previous.getContext('2d').drawImage(canvas, 0, 0);
      canvas.width = Math.max(1, Math.round(previous.width * .85));
      canvas.height = Math.max(1, Math.round(previous.height * .85));
      canvas.getContext('2d', { alpha: false }).drawImage(
        previous,
        0,
        0,
        canvas.width,
        canvas.height
      );
      best = await canvasToBlob(canvas, .42);
    }

    return new File([best], 'foto.jpg', {
      type: 'image/jpeg',
      lastModified: Date.now()
    });
  }

  function canvasToBlob(canvas, quality) {
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        blob => blob ? resolve(blob) : reject(new Error('No se pudo comprimir la fotografía.')),
        'image/jpeg',
        quality
      );
    });
  }

  function showPreview(element, file) {
    const image = element.querySelector('.vista-imagen');
    const frame = element.querySelector('.marco-recuerdo');
    const url = URL.createObjectURL(file);
    image.src = url;
    image.classList.add('visible');
    image.onload = () => URL.revokeObjectURL(url);
    frame.classList.add('visible');
  }

  function formatBytes(bytes) {
    return bytes >= 1024 * 1024
      ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
      : `${Math.round(bytes / 1024)} KB`;
  }

  function escapeHtml(value) {
    const container = document.createElement('div');
    container.textContent = value;
    return container.innerHTML;
  }
});
