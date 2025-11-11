// app.js - improved frontend logic with drag & drop and pretty chooser
const uploadForm = document.getElementById('uploadForm');
const csvInput = document.getElementById('csvfile');
const fileDrop = document.getElementById('fileDrop');
const chosenFiles = document.getElementById('chosenFiles');
const status = document.getElementById('status');
const errorBox = document.getElementById('error');
const results = document.getElementById('results');
const metricsDiv = document.getElementById('metrics');
const tsneImg = document.getElementById('tsneImg');
const downloadCsv = document.getElementById('downloadCsv');
const summaryDiv = document.getElementById('summary');

let currentFiles = [];

const footerEl = document.querySelector('.footer');

/**
 * Toggle footer between fixed (initial) and static (part of flow).
 * @param {boolean} makeStatic - true => move footer below content; false => fixed near bottom
 */
function setFooterStatic(makeStatic) {
  if (!footerEl) return;
  if (makeStatic) {
    footerEl.classList.add('footer--static');
  } else {
    footerEl.classList.remove('footer--static');
    // ensure it's visible when fixed
    footerEl.style.opacity = '1';
  }
}

function showError(msg){
  errorBox.style.display = 'block';
  errorBox.innerText = 'Error: ' + msg;
  status.innerText = '';
  results.style.display = 'none';
  setFooterStatic(false);
}

function clearError(){
  errorBox.style.display = 'none';
  errorBox.innerText = '';
}

function updateChosenUI(){
  if (!currentFiles || currentFiles.length === 0) {
    chosenFiles.innerText = 'No file chosen';
  } else if (currentFiles.length === 1) {
    chosenFiles.innerText = currentFiles[0].name;
  } else {
    chosenFiles.innerText = `${currentFiles.length} files selected`;
  }
}

// clicking .btn-file triggers file input because label points to it
csvInput.addEventListener('change', (e) => {
  currentFiles = Array.from(e.target.files || []);
  updateChosenUI();
});

// drag & drop
fileDrop.addEventListener('dragover', (e) => {
  e.preventDefault();
  fileDrop.classList.add('dragover');
});
fileDrop.addEventListener('dragleave', (e) => {
  e.preventDefault();
  fileDrop.classList.remove('dragover');
});
fileDrop.addEventListener('drop', (e) => {
  e.preventDefault();
  fileDrop.classList.remove('dragover');
  const dt = e.dataTransfer;
  if (dt && dt.files && dt.files.length) {
    csvInput.files = dt.files; // set native input so form works if user submits
    currentFiles = Array.from(dt.files);
    updateChosenUI();
  }
});

// main submit
uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();
  if (!csvInput.files || csvInput.files.length === 0) {
    return showError('Please choose a CSV file to upload.');
  }
  const f = csvInput.files[0];
  const k = parseInt(document.getElementById('k').value || '4', 10);

  status.innerText = 'Uploading file and running analysis...';
  results.style.display = 'none';
  summaryDiv.innerHTML = '';
  metricsDiv.innerHTML = '';

  const formData = new FormData();
  formData.append('file', f);
  formData.append('k', k);

  try {
    const resp = await fetch('/api/upload-and-analyze', {
      method: 'POST',
      body: formData
    });
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(text || `Server returned ${resp.status}`);
    }
    const data = await resp.json();

    status.innerText = '';
    results.style.display = 'block';
    setFooterStatic(true);
    metricsDiv.innerHTML = `
      <p><strong>Silhouette score:</strong> ${Number(data.silhouette).toFixed(4)}</p>
      <p><strong>Number of clusters:</strong> ${data.k}</p>
      <p><strong>Notes:</strong> ${data.notes}</p>
    `;
    if (data.plot_path) {
      tsneImg.src = `/uploads/${data.plot_path}?_=${Date.now()}`;
    } else {
      tsneImg.src = '';
    }
    if (data.csv_path) {
      downloadCsv.href = `/uploads/${data.csv_path}`;
      downloadCsv.style.display = 'inline-block';
    } else {
      downloadCsv.style.display = 'none';
    }

    // render summary if present
    if (data.summary) {
      let html = '<h4>Cluster summaries</h4><ul>';
      Object.keys(data.summary).forEach(clusterKey => {
        const s = data.summary[clusterKey];
        html += `<li><strong>Cluster ${clusterKey}</strong> — count: ${s.count} (${(s.pct*100).toFixed(1)}%)<br>
                 top movie: ${s.movie_genre_top1}, top series: ${s.series_genre_top1}<br>
                 top OTT: ${s.ott_top1}, top language: ${s.content_lang_top1}</li>`;
      });
      html += '</ul>';
      summaryDiv.innerHTML = html;
    }

  } catch (err) {
    console.error(err);
    showError(err.message || 'Unexpected error');
  }
});
