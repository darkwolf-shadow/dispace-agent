import fs from 'fs';
const filePath = 'C:/Users/Administrator/repos/ai-lead-platform-proposal/mangiafuoco/www/bot-avatar.png';
const form = new FormData();
form.append('type', 'image');
form.append('caption', 'foto test');
form.append('tags', 'test');
form.append('send_to_telegram', 'true');
form.append('file', new Blob([fs.readFileSync(filePath)]), 'capture.jpg');
const res = await fetch('https://dispace-agent-production.up.railway.app/mangiafuoco/memories', {
  method: 'POST',
  body: form,
});
console.log(res.status, await res.text());
