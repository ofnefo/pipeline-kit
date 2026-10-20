// Presentation of connected workflows; never adds or changes backend capabilities.
import {VIDEO_TASKS, videoTasks, modeLabel} from './models-modes.js?v=20261013';
const LOCAL = {
 video_rife:['RIFE','Повысить плавность','Добавьте промежуточные кадры. Например, 16 → 24 кадра/с. Длина ролика сохраняется; движение камеры не исправляется.'],
 video_esrgan:['Real-ESRGAN','Увеличить разрешение ×2','Увеличьте ширину и высоту вдвое. Создаётся новая копия с прежней частотой кадров.'],
 h3_flf:['MiniMax H3','Первый и последний кадр','Переход между двумя изображениями. Опишите движение внутри сцены.'],
 h3_i2v:['MiniMax H3','Оживить кадр','Загрузите изображение и опишите движение объекта и камеры.'],
 h3_t2v:['MiniMax H3','Видео по описанию','Опишите сцену, действие и движение камеры. Исходное изображение не нужно.'],
 h3_flf_depth:['MiniMax H3','Два кадра + движение из видео','Загрузите начальный и конечный кадры, затем видео для контроля движения.'],
 h3_ref2va:['MiniMax H3','По видео, фото или аудио','Добавьте хотя бы один образец. Модель создаст новую сцену по нему; точное сохранение кадров исходного видео не гарантируется.'],
 h3_last:['MiniMax H3','К последнему кадру','Загрузите изображение, которым должна завершиться сцена.'],
 ltx25_t2v:['LTX 2.5','Видео по описанию','Опишите сцену и движение. Изображение не требуется.'],
 ltx25_i2v:['LTX 2.5','Оживить кадр','Загрузите первый кадр и опишите действие.'],
 ltx25_last:['LTX 2.5','К последнему кадру','Загрузите изображение, которым должна завершиться сцена.'],
 wan22_i2v14b:['Wan 2.2','Оживить кадр','Загрузите первый кадр и опишите действие. Последний кадр не требуется.'],
 infinitetalk_single:['InfiniteTalk','Оживить говорящий портрет','Загрузите портрет и запись речи для синхронизации губ.'],
 ltx25_clean_plate:['LTX 2.5','Переработать видео','Исходное видео задаёт движение, описание — желаемое содержимое сцены.'],
 ltx25_flf:['LTX 2.5','Первый и последний кадр','Задайте начало и конец сцены двумя изображениями.'],
 seedvr2_upscale_image:['SeedVR2','Улучшить изображение','Увеличьте разрешение готовой картинки.'],
 seedvr2_upscale_video:['SeedVR2','Улучшить видео','Увеличьте разрешение готового ролика.'],
 wan21_uni3c:['Wan Uni3C','Движение камеры по образцу','Нужны изображение сцены и видео с заданным движением камеры.'],
 wan22_animate:['Wan Animate 2','Перенести движение на персонажа','Изображение задаёт персонажа, видео — его движения.'],
 wan22_fun_camera:['Wan Fun Camera','Оживить кадр с движением камеры','Загрузите картинку и выберите движение камеры.'],
 wan22_i2v14b_flf:['Wan 2.2','Первый и последний кадр','Соедините два кадра в одну сцену и опишите действие.'],
 wan22_svi_long:['Wan 2.2','Длинная сцена по эпизодам','Загрузите первый кадр. Опишите шесть последовательных эпизодов одной сцены.'],
 wan22_vace_a14b_inpaint:['Wan VACE','Заменить область в видео','Нужны ролик и видео-маска области, которую нужно изменить.'],
 wan22_vace_a14b_v2v:['Wan VACE','Переработать видео','Загрузите ролик и опишите, как изменить его содержимое.'],
 design_cutout_birefnet:['BiRefNet','Убрать фон','Получите изображение на прозрачном фоне и отдельную маску.'],
 design_edit_qwen2511:['Qwen Image Edit','Правка по описанию','Загрузите картинку и опишите, что нужно изменить.'],
 design_edit_qwen2511_lora:['Qwen Image Edit','Правка с дополнительным стилем','Правка изображения с выбранной LoRA. Файл стиля задаётся отдельно.'],
 design_face_restore_codeformer:['CodeFormer','Восстановить лицо','Восстановление деталей лица на готовой фотографии.'],
 design_t2i_qwen21:['Qwen Image 2.1','Картинка по описанию','Опишите сюжет, композицию и стиль изображения.'],
 design_t2i_sdxl_turbo:['SDXL Turbo','Быстрый эскиз','Создайте черновую картинку по описанию.'],
 design_t2i_zimage_controlnet:['Z-Image Turbo','Картинка по контуру или позе','Загрузите управляющее изображение и опишите нужный результат.'],
 design_t2i_zimage_turbo:['Z-Image Turbo','Картинка по описанию','Опишите сюжет, композицию и стиль изображения.'],
 chord_material:['CHORD','Материал по фото','Получите карты материала из фотографии поверхности.'],
 hunyuan3d21_image_to_mesh:['Hunyuan3D 2.1','3D-модель по фото','Загрузите изображение объекта для восстановления его формы.'],
 image_to_scene_moge2:['MoGe 2','Геометрия сцены по фото','Восстановите пространственную геометрию по одному изображению.'],
 image_to_scene_sam3:['SAM 3','Выделить объект','Опишите объект на фотографии, чтобы получить его маску.'],
 trellis2_image_to_3d:['TRELLIS 2','3D-модель по фото','Загрузите изображение объекта для создания 3D-модели.'],
 music_acestep15_xl_sft_t2m:['ACE-Step','Музыка по описанию','Задайте жанр, настроение и инструменты. Текст песни нужен только для вокала.'],
 music_acestep15_xl_sft_remix:['ACE-Step','Новая версия трека','Загрузите трек и опишите стиль новой версии.'],
 music_acestep15_xl_sft_repaint:['ACE-Step','Заменить фрагмент трека','Загрузите аудио и укажите начало и конец фрагмента для замены.'],
 music_acestep15_xl_sft_extend:['ACE-Step','Продолжить трек','Загрузите аудио и опишите его продолжение.'],
 music_sfx_stable_audio_open:['Stable Audio Open','Звук по описанию','Создайте звуковой эффект или атмосферу сцены.'],
 stems:['RoFormer','Разделить трек','Разделите запись на голос и инструментальные дорожки.'],
 tts_design:['Qwen3-TTS','Создать голос','Опишите голос и введите текст, который он произнесёт.'],
 tts_clone:['Qwen3-TTS','Озвучить выбранным голосом','Выберите сохранённый голос или загрузите образец речи.'],
 tts_cosy_zero:['CosyVoice 3','Голос по записи и её тексту','Нужны образец речи и точный текст, произнесённый в нём.'],
 tts_cosy_cross:['CosyVoice 3','Голос по записи','Выберите сохранённый голос или загрузите образец речи.'],
 tts_xtts_draft:['XTTS v2','Черновая озвучка','Быстрый черновик с голосом из образца речи.'],
 tts_omni_clone:['OmniVoice','Озвучить выбранным голосом','Выберите сохранённый голос или загрузите образец речи 5–20 с. Темп 0,85 подобран для вашего голоса.'],
 tts_omni_design:['OmniVoice','Создать голос','Выберите пол, возраст и высоту голоса, введите текст.']
};
// One model = one entry in «Модель»; workflows on the same weights become its «Режим».
const FAMILY = {ltx25_clean_plate:'ltx25', design_t2i_zimage_controlnet:'zimage', wan22_svi_long:'wan22'};
export const familyKey = it => FAMILY[it.id] || (/^h3_(flf|flf_depth|i2v|t2v)$/.test(it.id) ? 'h3' : it.cloud ? it.id : it.base || it.id);
export const familyRank = it => FAMILY[it.id] ? 1 : 0;
// Readable run name for lists outside Модели (Главная): «Модель · режим», null if the mode has no Russian name.
export const runName = kind => LOCAL[kind] ? LOCAL[kind][0] + ' · ' + LOCAL[kind][1] : null;
export const modelName = it => LOCAL[it.id]?.[0] || (it.cloud ? it.title : it.base_title || it.title).split(' (')[0];
export const variantName = it => LOCAL[it.id]?.[1] || modeLabel(it) || 'Основной';
export function modelPurpose(it) {
 if(LOCAL[it.id]) return LOCAL[it.id][2];
 if(it.group==='video') return 'Доступные задачи: '+videoTasks(it).map(k=>VIDEO_TASKS.find(t=>t[0]===k)?.[1]||k).join(', ')+'. Стоимость рассчитывается перед запуском.';
 if(it.cloud && /remove-background/.test(it.id))return 'Удалите фон изображения. Стоимость рассчитывается перед запуском.';
 if(it.cloud && /edit|kontext/.test(it.id))return 'Загрузите изображение и опишите правки. Стоимость рассчитывается перед запуском.';
 if(it.cloud) return 'Создайте изображение по описанию'+(it.fields.some(f=>f.kind==='upload')?' или добавьте визуальные образцы':'')+'. Стоимость рассчитывается перед запуском.';
 return it.about || it.note || 'Выберите исходники и заполните описание результата.';
}
export function tasksFor(it) {
 if(it.group==='video')return videoTasks(it);
 if(it.group==='image') {
  if(/birefnet|remove-background/.test(it.id))return ['cutout'];
  if(/codeformer|upscale/.test(it.id))return ['enhance'];
  if(/controlnet/.test(it.id))return ['guided'];
  if(/edit|kontext/.test(it.id))return ['edit'];
  return ['create'];
 }
 if(it.group==='3d') return [/chord/.test(it.id)?'material':/sam3/.test(it.id)?'mask':/moge/.test(it.id)?'scene':'mesh'];
 if(it.group==='music')return [it.id==='stems'?'stems':/sfx/.test(it.id)?'sfx':it.mode||'t2m'];
 return [/^tts_(omni_)?design$/.test(it.id)?'design':'speak'];
}
const TASKS={image:[['create','Создать картинку'],['edit','Изменить картинку'],['guided','По контуру или позе'],['cutout','Убрать фон'],['enhance','Улучшить качество']],
 '3d':[['mesh','Модель по фото'],['scene','Сцена по фото'],['material','Материал по фото'],['mask','Выделить объект']],
 music:[['t2m','Создать музыку'],['remix','Новая версия трека'],['repaint','Заменить фрагмент'],['extend','Продолжить трек'],['stems','Разделить трек'],['sfx','Создать звук']],
 voice:[['design','Создать голос'],['speak','Озвучить текст']]};
export const taskOptions = group => group==='video'?VIDEO_TASKS:[['all','Все задачи'],...(TASKS[group]||[])];
const LABELS={cfg:'Точность следования описанию (CFG)',shift:'Сдвиг расписания (shift)',denoise:'Сила изменения',feather:'Плавность стыка, с',cover_strength:'Близость к исходнику',lm_cfg_scale:'Точность языковой модели',lm_temperature:'Свобода языковой модели',generate_audio_codes:'Продумать структуру песни',prompt:'Описание результата',negative:'Чего избегать',motion_prompt:'Движения персонажа',text:'Текст для озвучки',instruct:'Каким должен быть голос',tags:'Стиль музыки',lyrics:'Текст песни',
 start_image:'Первый кадр',end_image:'Последний кадр',first_frame_image:'Первый кадр',last_frame_image:'Последний кадр',last_frame:'Последний кадр',last_image:'Последний кадр',image:'Изображение',input_image:'Исходное изображение',input_reference:'Исходное изображение',reference_image:'Персонаж',ref_image:'Визуальный образец',ref_video:'Видеореференс',control_image:'Контур, поза или карта глубины',input_video:'Исходное видео',control_video:'Видео для управления движением',mask_video:'Видео-маска области замены',drive_video:'Образец движения',render_video:'Видео с движением камеры',audio:'Запись речи',ref_audio:'Образец голоса',source_audio:'Исходный трек',ref_text:'Текст, произнесённый в образце',
 width:'Ширина, px',height:'Высота, px',length:'Длина, кадров',fps:'Кадров в секунду',steps:'Шаги генерации',seed:'Номер варианта (seed)',duration:'Длительность, с',seconds:'Длительность, с',extend_seconds:'Продолжение, с',start:'Начало замены, с',end:'Конец замены, с',mask_start:'Начало участка, с',bpm:'Темп, BPM',keyscale:'Тональность',timesignature:'Музыкальный размер',language:'Язык',resolution:'Разрешение',aspect_ratio:'Формат кадра',ratio:'Формат кадра',generate_audio:'Звук в ролике',generate_audio_switch:'Звук в ролике',budget_project:'Бюджет проекта',extra_lora:'Файл дополнительного стиля (LoRA)',extra_lora_strength:'Сила дополнительного стиля',camera_pose:'Движение камеры',speed:'Скорость движения',filename_prefix:'Префикс имени файла',dit_model:'Файл модели',batch_size:'Размер пакета',faces:'Число граней',texture_size:'Размер текстуры',save_voice_name:'Название нового голоса',quality:'Качество',number_of_images:'Количество изображений',output_format:'Формат файла',background:'Фон'};
const MAIN=new Set(['prompt','motion_prompt','text','instruct','tags','lyrics','voice_preset','ref_text','voice_rights','save_voice_name','duration','seconds','extend_seconds','start','end','mask_start','bpm','language','resolution','aspect_ratio','ratio','generate_audio','generate_audio_switch','budget_project','camera_pose','speed','format','mode','quality','number_of_images','output_format','background','size']);
const OPTIONS={voice_rights:{owned:'Мой голос',licensed:'Есть лицензия',synthetic:'Синтетический голос'},
 language:{ru:'Русский',en:'Английский',auto:'Определить автоматически',de:'Немецкий',es:'Испанский',fr:'Французский',it:'Итальянский',ja:'Японский',ko:'Корейский',pt:'Португальский',zh:'Китайский'}};
export const optionLabel=(f,c)=>f.option_labels?.[c]||OPTIONS[f.name]?.[c]||c;
export function fieldMeta(f,it) {
 let label=LABELS[f.name]||f.label||f.name,help='';
 const segment=/^prompt_(\d+)$/.exec(f.name);
 if(segment){label=Number(segment[1])===1?'Начало сцены':'Продолжение · эпизод '+segment[1];help=Number(segment[1])===1?'Что происходит после первого кадра.':'Что должно произойти дальше в этой же сцене.';}
 if(/^ref\d+$/.test(f.name))label='Визуальный образец '+f.name.slice(3);
 if(f.name==='text' && it.id==='image_to_scene_sam3')label='Какой объект выделить';
 if(f.name==='control_video' && /vace/.test(it.id))label='Исходное видео';
 if(f.name==='ref_audio' && it.id==='h3_ref2va')label='Образец звука или голоса';
 if(f.name==='speed' && /^tts_/.test(it.id))label='Темп речи';
 if(f.name==='source_audio')help='Загрузите трек, который нужно продолжить или переделать.';
 if(f.name==='ref_video' && it.id==='h3_ref2va')help='Первые 5,17 с видео (минимум 2 с). Картинка отдельно не нужна. Звуковая дорожка образца не используется. Это ориентир для новой сцены, а не точная правка исходника.';
 if(f.name==='model' && it.id==='replicate_seedance')label='Версия Seedance';
 if(f.name==='length')help='Число кадров в workflow. Меняйте только если нужна другая длина ролика.';
 if(f.name==='prompt')help=it.group==='image'?'Опишите сюжет или нужные изменения.':it.group==='music'?'Опишите звук, его характер и окружение.':'Опишите действие, обстановку и движение камеры.';
 if(f.name==='ref_text' && it.id==='tts_cosy_zero')help='Укажите точный текст образца, если он не задан в сохранённом голосе.';
 return {label,help,main:!!(f.required||f.kind==='upload'||segment||MAIN.has(f.name)||(f.name==='model'&&it.id==='replicate_seedance'))};
}
