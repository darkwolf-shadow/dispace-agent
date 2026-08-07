import fs from 'fs';
const token = process.env.TOKEN;
const chatId = '7254908257';
const filePath = 'C:/Users/Administrator/repos/ai-lead-platform-proposal/mangiafuoco/www/bot-avatar.png';
const form = new FormData();
form.append('chat_id', chatId);
form.append('caption', '#memoria Mangiafuoco\n\nfoto test\n\nTag: test');
form.append('parse_mode', 'HTML');
form.append('photo', new Blob([fs.readFileSync(filePath)]));
const res = await fetch(`https://api.telegram.org/bot${token}/sendPhoto`, {
  method: 'POST',
  body: form,
});
console.log(res.status, await res.text());
