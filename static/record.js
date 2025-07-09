
let mediaRecorder;
let audioChunks = [];

const nextBtn = document.getElementById('nextBtn');
const stopBtn = document.getElementById('stopBtn');
const loadIcon = document.getElementById('loadIcon');
const phraseEl = document.getElementById('phrase');
const checklistBtn = document.getElementById('checklistBtn');
const checklistModal = document.getElementById('checklistModal');
const outputTextEl = document.querySelector("#outputText span");
const expectedStressEl = document.querySelector("#expectedStress span");
const receivedStressEl = document.querySelector("#receivedStress span");
const result = document.getElementById('result');
if (phraseEl) {
    const phrase = phraseEl.textContent.replace(/ /g, '_').replace(/[?!]/g, '');
    const userData = new FormData();
    userData.append('phrase', phrase);

    fetch('/load', {
        method: 'POST',
        body: userData
    })
    .then(response => response.json())
    .then(data => {
        if (data.colorCode) {
            applyColorMapping(data.syllables, data.colorCode);
        }
    })
    .catch(error => {
        console.error('Error loading user data:', error);
    });
}

function applyColorMapping(syllables, colorCode) {
    const colors = {
        "1": "#90ee90",
        "2": "#ff4c4c",
        "3": "#f5d142"
    };

    const colored = syllables.map((syll, i) => {
        const color = colors[colorCode[i]] || "white";
        const syllSpaced = syll.replace(/ /g, '&nbsp;');
        return `<span style="color:${color}">${syllSpaced}</span>`;
    }).join('');

    const cebuanoEl = document.querySelector(".cebuano");
    if (cebuanoEl) {
        cebuanoEl.innerHTML = colored;
    }
}

if (nextBtn) {
    nextBtn.addEventListener('click', async (e) => {
        e.preventDefault();

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const audioUrl = URL.createObjectURL(audioBlob);
                new Audio(audioUrl).play();

                const formData = new FormData();
                formData.append('audio', audioBlob, 'recording.webm');

                const pageName = window.location.pathname.split("/").pop().replace('.html', '');
                formData.append('page_name', pageName);

                if (loadIcon) loadIcon.style.display = 'inline-block';
                nextBtn.style.display = 'none';

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.color_code && data.syllables) {
                        applyColorMapping(data.syllables, data.color_code);
                        result.style.display = 'block';
                        if (outputTextEl) outputTextEl.textContent = data.output_text || '';
                        if (expectedStressEl) expectedStressEl.textContent = data.expected_stress || '';
                        if (receivedStressEl) receivedStressEl.textContent = data.received_stress || '';
                    }
                })
                .catch(error => {
                    console.error('Upload error:', error);
                })
                .finally(() => {
                    if (loadIcon) loadIcon.style.display = 'none';
                    nextBtn.style.display = 'inline-block';
                });
            };

            mediaRecorder.start();
            if (stopBtn) stopBtn.style.display = 'inline-block';
            nextBtn.style.display = 'none';

        } catch (err) {
            alert('Microphone access denied or not available.');
            console.error(err);
        }
    });
}

if (stopBtn) {
    stopBtn.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            stopBtn.style.display = 'none';
            nextBtn.style.display = 'inline-block';
        }
    });
}

if (checklistBtn && checklistModal) {
    checklistBtn.addEventListener('click', () => {
        checklistModal.style.display = 'block';
    });

    window.addEventListener('click', (event) => {
        if (event.target === checklistModal) {
            checklistModal.style.display = 'none';
        }
    });
}

