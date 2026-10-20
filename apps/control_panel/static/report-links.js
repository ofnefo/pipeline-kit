// Public distribution: local project files are available; remote sharing is optional.
export const projectPath = row => row.local_path || '';
export function deliveryReceiptHTML() {
  return '<p role="status">Внешняя доставка не настроена. Сохраните результат локально через файловый браузер.</p>';
}
export async function openReportLinks() {
  let dialog=document.getElementById('report-links-dialog');
  if(!dialog){dialog=document.createElement('dialog');dialog.id='report-links-dialog';document.body.append(dialog);}
  dialog.innerHTML='<div class="board-dialog-head"><h2>Отчёты и ссылки</h2><button type="button" class="ghost" aria-label="Закрыть">✕</button></div><p>Публичные ссылки и отправка сообщений требуют отдельного адаптера. Откройте локальные отчёты в файловом браузере проекта.</p>';
  dialog.querySelector('button').onclick=()=>dialog.close();
  if(!dialog.open)dialog.showModal();
}
