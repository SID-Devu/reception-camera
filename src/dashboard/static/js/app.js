const app = new Vue({
    el: '#app',
    data: {
        message: 'Welcome to the Reception Camera Dashboard!',
        recognizedPerson: null,
        logs: [],
    },
    methods: {
        greetPerson(name) {
            this.recognizedPerson = name;
            this.logs.push(`Greeted ${name} at ${new Date().toLocaleTimeString()}`);
            this.speakGreeting(name);
        },
        speakGreeting(name) {
            const utterance = new SpeechSynthesisUtterance(`Hello, ${name}! Welcome!`);
            window.speechSynthesis.speak(utterance);
        },
        fetchLogs() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    this.logs = data;
                });
        },
        clearLogs() {
            this.logs = [];
        }
    },
    mounted() {
        this.fetchLogs();
    }
});