// Classify only connected forms, not theoretical capabilities of the underlying model.
export const VIDEO_TASKS = [
  ['all', 'Все варианты'], ['t2v', 'Текст → видео'], ['i2v', 'Кадр → видео'],
  ['flf', 'Первый + последний кадр'], ['last', 'К последнему кадру'], ['reference', 'По образцам'], ['v2v', 'Видео → видео'],
  ['inpaint', 'Заменить часть видео'], ['voice', 'Озвучить персонажа'],
  ['upscale', 'Улучшить видео'], ['other', 'Другие задачи'],
];
const LOCAL_TASKS = {
  h3_last:['last'], ltx25_t2v:['t2v'], ltx25_i2v:['i2v'], ltx25_last:['last'], wan22_i2v14b:['i2v'],
  h3_i2v: ['i2v'], h3_t2v: ['t2v'], h3_flf: ['flf'], h3_flf_depth: ['flf', 'v2v'], ltx25_flf: ['flf'],
  wan22_i2v14b_flf: ['flf'], wan22_vace_a14b_v2v: ['v2v'],
  wan22_vace_a14b_inpaint: ['inpaint'], wan22_animate: ['v2v'],
  wan21_uni3c: ['v2v'], ltx25_clean_plate: ['v2v'],
  wan22_svi_long: ['i2v'], wan22_fun_camera: ['i2v'],
  h3_ref2va: ['reference', 'voice'], infinitetalk_single: ['voice'], seedvr2_upscale_video: ['upscale'], video_rife: ['upscale'], video_esrgan: ['upscale'],
};
export function videoTasks(it) {
  const task = {first_frame:'i2v',last_frame:'last',text:'t2v',first_last_frame:'flf',first_last_depth:'flf',reference_to_video:'reference',video_to_video:'v2v',masked_video_to_video:'inpaint',motion_transfer:'v2v',latent_continuation:'i2v',audio_driven_portrait:'voice',video_upscale:'upscale'}[it.video_contract?.mode];
  if (task) return [task];
  if (LOCAL_TASKS[it.id]) return LOCAL_TASKS[it.id];
  if (it.id === 'replicate_seedance') return ['t2v'];
  if (it.cloud && it.group === 'video') {
    const uploads = it.fields.filter(f => f.kind === 'upload');
    const first = uploads.find(f => ['image', 'start_image', 'first_frame_image', 'input_reference'].includes(f.name));
    const last = uploads.find(f => ['last_frame', 'end_image', 'last_image', 'last_frame_image'].includes(f.name));
    const tasks = [];
    if (!uploads.some(f => f.required)) tasks.push('t2v');
    if (first) tasks.push('i2v');
    if (uploads.some(f=>['video','input_video','reference_video'].includes(f.name))) tasks.push('v2v');
    if (first && last) tasks.push('flf');
    return tasks.length ? tasks : ['other'];
  }
  return ['other'];
}
export const taskLabel = key => VIDEO_TASKS.find(t => t[0] === key)?.[1] || key;
export const modeLabel = it => ({last:'К последнему кадру',reference:'По видео, фото или аудио',i2v:'Кадр → видео', t2v:'Текст → видео', flf:'Первый + последний кадр', depth:'Кадры + контроль движения',
  v2v:'Видео → видео', inpaint:'Заменить часть видео', t2i:'Текст → картинка',
  t2m:'Создать музыку', remix:'Ремикс', repaint:'Заменить фрагмент', extend:'Продолжить'}[it.mode] || it.mode || '');
