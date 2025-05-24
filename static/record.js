let mediaRecorder;
let audioChunks = [];

const nextBtn = document.getElementById('nextBtn');
const stopBtn = document.getElementById('stopBtn');

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
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play(); // Optional: play back the recording

            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');

            const pageName = window.location.pathname.split("/").pop().replace('.html', '');
            formData.append('page_name', pageName);

            fetch('https://how-collections-genealogy-gibson.trycloudflare.com/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Upload success:', data);

                const code = data.color_code; 
                const syllables = data.syllables;
                const colors = {
                    "1": "#90ee90", // green
                    "2": "#ff4c4c", // red
                    "3": "#f5d142"  // yellow
                };

                const colored = syllables.map((syll, i) => {
                    const color = colors[code[i]] || "white";
                    return `<span style="color:${color}">${syll}</span>`;
                }).join('');

                document.querySelector(".cebuano").innerHTML = colored;
            })
            .catch(error => {
                console.error('Upload error:', error);
            });
        };

        mediaRecorder.start();
        stopBtn.style.display = 'inline-block';
        nextBtn.style.display = 'none';
    } catch (err) {
        alert('Microphone access denied or not available.');
        console.error(err);
    }
});

stopBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        stopBtn.style.display = 'none';
        nextBtn.style.display = 'inline-block';
    }
});

