import { formatInTimeZone } from 'date-fns-tz'

export const COMMON_TIMEZONES = [
  { value: 'UTC', label: { en: 'UTC (GMT+0:00)', zh: 'UTC (GMT+0:00)' } },

  // Americas - West to East
  {
    value: 'Pacific/Midway',
    label: {
      en: 'Pacific/Midway (GMT-11:00)',
      zh: 'Pacific/Midway (GMT-11:00)'
    }
  },
  {
    value: 'Pacific/Honolulu',
    label: {
      en: 'Pacific/Honolulu (GMT-10:00) - Hawaii',
      zh: 'Pacific/Honolulu (GMT-10:00) - 夏威夷'
    }
  },
  {
    value: 'America/Anchorage',
    label: {
      en: 'America/Anchorage (GMT-9:00) - Alaska',
      zh: 'America/Anchorage (GMT-9:00) - 阿拉斯加'
    }
  },
  {
    value: 'America/Los_Angeles',
    label: {
      en: 'America/Los_Angeles (GMT-8:00) - Los Angeles/San Francisco',
      zh: 'America/Los_Angeles (GMT-8:00) - 洛杉矶/旧金山'
    }
  },
  {
    value: 'America/Phoenix',
    label: {
      en: 'America/Phoenix (GMT-7:00) - Phoenix',
      zh: 'America/Phoenix (GMT-7:00) - 凤凰城'
    }
  },
  {
    value: 'America/Denver',
    label: {
      en: 'America/Denver (GMT-7:00) - Denver',
      zh: 'America/Denver (GMT-7:00) - 丹佛'
    }
  },
  {
    value: 'America/Chicago',
    label: {
      en: 'America/Chicago (GMT-6:00) - Chicago',
      zh: 'America/Chicago (GMT-6:00) - 芝加哥'
    }
  },
  {
    value: 'America/Mexico_City',
    label: {
      en: 'America/Mexico_City (GMT-6:00) - Mexico City',
      zh: 'America/Mexico_City (GMT-6:00) - 墨西哥城'
    }
  },
  {
    value: 'America/New_York',
    label: {
      en: 'America/New_York (GMT-5:00) - New York/Washington',
      zh: 'America/New_York (GMT-5:00) - 纽约/华盛顿'
    }
  },
  {
    value: 'America/Toronto',
    label: {
      en: 'America/Toronto (GMT-5:00) - Toronto',
      zh: 'America/Toronto (GMT-5:00) - 多伦多'
    }
  },
  {
    value: 'America/Caracas',
    label: {
      en: 'America/Caracas (GMT-4:00) - Caracas',
      zh: 'America/Caracas (GMT-4:00) - 加拉加斯'
    }
  },
  {
    value: 'America/Halifax',
    label: {
      en: 'America/Halifax (GMT-4:00) - Halifax',
      zh: 'America/Halifax (GMT-4:00) - 哈利法克斯'
    }
  },
  {
    value: 'America/St_Johns',
    label: {
      en: 'America/St_Johns (GMT-3:30) - Newfoundland',
      zh: 'America/St_Johns (GMT-3:30) - 纽芬兰'
    }
  },
  {
    value: 'America/Buenos_Aires',
    label: {
      en: 'America/Buenos_Aires (GMT-3:00) - Buenos Aires',
      zh: 'America/Buenos_Aires (GMT-3:00) - 布宜诺斯艾利斯'
    }
  },
  {
    value: 'America/Sao_Paulo',
    label: {
      en: 'America/Sao_Paulo (GMT-3:00) - São Paulo',
      zh: 'America/Sao_Paulo (GMT-3:00) - 圣保罗'
    }
  },
  {
    value: 'Atlantic/Cape_Verde',
    label: {
      en: 'Atlantic/Cape_Verde (GMT-1:00)',
      zh: 'Atlantic/Cape_Verde (GMT-1:00)'
    }
  },

  // Europe & Africa
  {
    value: 'Europe/London',
    label: {
      en: 'Europe/London (GMT+0:00) - London',
      zh: 'Europe/London (GMT+0:00) - 伦敦'
    }
  },
  {
    value: 'Europe/Dublin',
    label: {
      en: 'Europe/Dublin (GMT+0:00) - Dublin',
      zh: 'Europe/Dublin (GMT+0:00) - 都柏林'
    }
  },
  {
    value: 'Africa/Lagos',
    label: {
      en: 'Africa/Lagos (GMT+1:00) - Lagos',
      zh: 'Africa/Lagos (GMT+1:00) - 拉各斯'
    }
  },
  {
    value: 'Europe/Paris',
    label: {
      en: 'Europe/Paris (GMT+1:00) - Paris',
      zh: 'Europe/Paris (GMT+1:00) - 巴黎'
    }
  },
  {
    value: 'Europe/Berlin',
    label: {
      en: 'Europe/Berlin (GMT+1:00) - Berlin',
      zh: 'Europe/Berlin (GMT+1:00) - 柏林'
    }
  },
  {
    value: 'Europe/Rome',
    label: {
      en: 'Europe/Rome (GMT+1:00) - Rome',
      zh: 'Europe/Rome (GMT+1:00) - 罗马'
    }
  },
  {
    value: 'Europe/Madrid',
    label: {
      en: 'Europe/Madrid (GMT+1:00) - Madrid',
      zh: 'Europe/Madrid (GMT+1:00) - 马德里'
    }
  },
  {
    value: 'Europe/Amsterdam',
    label: {
      en: 'Europe/Amsterdam (GMT+1:00) - Amsterdam',
      zh: 'Europe/Amsterdam (GMT+1:00) - 阿姆斯特丹'
    }
  },
  {
    value: 'Europe/Athens',
    label: {
      en: 'Europe/Athens (GMT+2:00) - Athens',
      zh: 'Europe/Athens (GMT+2:00) - 雅典'
    }
  },
  {
    value: 'Africa/Cairo',
    label: {
      en: 'Africa/Cairo (GMT+2:00) - Cairo',
      zh: 'Africa/Cairo (GMT+2:00) - 开罗'
    }
  },
  {
    value: 'Africa/Johannesburg',
    label: {
      en: 'Africa/Johannesburg (GMT+2:00) - Johannesburg',
      zh: 'Africa/Johannesburg (GMT+2:00) - 约翰内斯堡'
    }
  },
  {
    value: 'Europe/Istanbul',
    label: {
      en: 'Europe/Istanbul (GMT+3:00) - Istanbul',
      zh: 'Europe/Istanbul (GMT+3:00) - 伊斯坦布尔'
    }
  },
  {
    value: 'Europe/Moscow',
    label: {
      en: 'Europe/Moscow (GMT+3:00) - Moscow',
      zh: 'Europe/Moscow (GMT+3:00) - 莫斯科'
    }
  },
  {
    value: 'Africa/Nairobi',
    label: {
      en: 'Africa/Nairobi (GMT+3:00) - Nairobi',
      zh: 'Africa/Nairobi (GMT+3:00) - 内罗毕'
    }
  },

  // Middle East & Central Asia
  {
    value: 'Asia/Dubai',
    label: {
      en: 'Asia/Dubai (GMT+4:00) - Dubai',
      zh: 'Asia/Dubai (GMT+4:00) - 迪拜'
    }
  },
  {
    value: 'Asia/Baku',
    label: {
      en: 'Asia/Baku (GMT+4:00) - Baku',
      zh: 'Asia/Baku (GMT+4:00) - 巴库'
    }
  },
  {
    value: 'Asia/Kabul',
    label: {
      en: 'Asia/Kabul (GMT+4:30) - Kabul',
      zh: 'Asia/Kabul (GMT+4:30) - 喀布尔'
    }
  },
  {
    value: 'Asia/Karachi',
    label: {
      en: 'Asia/Karachi (GMT+5:00) - Karachi',
      zh: 'Asia/Karachi (GMT+5:00) - 卡拉奇'
    }
  },
  {
    value: 'Asia/Tashkent',
    label: {
      en: 'Asia/Tashkent (GMT+5:00) - Tashkent',
      zh: 'Asia/Tashkent (GMT+5:00) - 塔什干'
    }
  },
  {
    value: 'Asia/Kolkata',
    label: {
      en: 'Asia/Kolkata (GMT+5:30) - Mumbai/New Delhi',
      zh: 'Asia/Kolkata (GMT+5:30) - 孟买/新德里'
    }
  },
  {
    value: 'Asia/Kathmandu',
    label: {
      en: 'Asia/Kathmandu (GMT+5:45) - Kathmandu',
      zh: 'Asia/Kathmandu (GMT+5:45) - 加德满都'
    }
  },
  {
    value: 'Asia/Dhaka',
    label: {
      en: 'Asia/Dhaka (GMT+6:00) - Dhaka',
      zh: 'Asia/Dhaka (GMT+6:00) - 达卡'
    }
  },
  {
    value: 'Asia/Almaty',
    label: {
      en: 'Asia/Almaty (GMT+6:00) - Almaty',
      zh: 'Asia/Almaty (GMT+6:00) - 阿拉木图'
    }
  },
  {
    value: 'Asia/Yangon',
    label: {
      en: 'Asia/Yangon (GMT+6:30) - Yangon',
      zh: 'Asia/Yangon (GMT+6:30) - 仰光'
    }
  },
  {
    value: 'Asia/Bangkok',
    label: {
      en: 'Asia/Bangkok (GMT+7:00) - Bangkok',
      zh: 'Asia/Bangkok (GMT+7:00) - 曼谷'
    }
  },
  {
    value: 'Asia/Jakarta',
    label: {
      en: 'Asia/Jakarta (GMT+7:00) - Jakarta',
      zh: 'Asia/Jakarta (GMT+7:00) - 雅加达'
    }
  },
  {
    value: 'Asia/Ho_Chi_Minh',
    label: {
      en: 'Asia/Ho_Chi_Minh (GMT+7:00) - Ho Chi Minh City',
      zh: 'Asia/Ho_Chi_Minh (GMT+7:00) - 胡志明市'
    }
  },

  // East Asia
  {
    value: 'Asia/Shanghai',
    label: {
      en: 'Asia/Shanghai (GMT+8:00) - China Beijing/Shanghai',
      zh: 'Asia/Shanghai (GMT+8:00) - 中国北京/上海'
    }
  },
  {
    value: 'Asia/Hong_Kong',
    label: {
      en: 'Asia/Hong_Kong (GMT+8:00) - China Hong Kong',
      zh: 'Asia/Hong_Kong (GMT+8:00) - 中国香港'
    }
  },
  {
    value: 'Asia/Taipei',
    label: {
      en: 'Asia/Taipei (GMT+8:00) - China Taipei',
      zh: 'Asia/Taipei (GMT+8:00) - 中国台北'
    }
  },
  {
    value: 'Asia/Macau',
    label: {
      en: 'Asia/Macau (GMT+8:00) - China Macau',
      zh: 'Asia/Macau (GMT+8:00) - 中国澳门'
    }
  },
  {
    value: 'Asia/Singapore',
    label: {
      en: 'Asia/Singapore (GMT+8:00) - Singapore',
      zh: 'Asia/Singapore (GMT+8:00) - 新加坡'
    }
  },
  {
    value: 'Asia/Manila',
    label: {
      en: 'Asia/Manila (GMT+8:00) - Manila',
      zh: 'Asia/Manila (GMT+8:00) - 马尼拉'
    }
  },
  {
    value: 'Asia/Kuala_Lumpur',
    label: {
      en: 'Asia/Kuala_Lumpur (GMT+8:00) - Kuala Lumpur',
      zh: 'Asia/Kuala_Lumpur (GMT+8:00) - 吉隆坡'
    }
  },
  {
    value: 'Asia/Ulaanbaatar',
    label: {
      en: 'Asia/Ulaanbaatar (GMT+8:00) - Ulaanbaatar',
      zh: 'Asia/Ulaanbaatar (GMT+8:00) - 乌兰巴托'
    }
  },

  // Japan & Korea
  {
    value: 'Asia/Tokyo',
    label: {
      en: 'Asia/Tokyo (GMT+9:00) - Tokyo',
      zh: 'Asia/Tokyo (GMT+9:00) - 东京'
    }
  },
  {
    value: 'Asia/Seoul',
    label: {
      en: 'Asia/Seoul (GMT+9:00) - Seoul',
      zh: 'Asia/Seoul (GMT+9:00) - 首尔'
    }
  },

  // Australia & Pacific
  {
    value: 'Australia/Perth',
    label: {
      en: 'Australia/Perth (GMT+8:00) - Perth',
      zh: 'Australia/Perth (GMT+8:00) - 珀斯'
    }
  },
  {
    value: 'Australia/Adelaide',
    label: {
      en: 'Australia/Adelaide (GMT+9:30) - Adelaide',
      zh: 'Australia/Adelaide (GMT+9:30) - 阿德莱德'
    }
  },
  {
    value: 'Australia/Darwin',
    label: {
      en: 'Australia/Darwin (GMT+9:30) - Darwin',
      zh: 'Australia/Darwin (GMT+9:30) - 达尔文'
    }
  },
  {
    value: 'Australia/Brisbane',
    label: {
      en: 'Australia/Brisbane (GMT+10:00) - Brisbane',
      zh: 'Australia/Brisbane (GMT+10:00) - 布里斯班'
    }
  },
  {
    value: 'Australia/Sydney',
    label: {
      en: 'Australia/Sydney (GMT+10:00) - Sydney',
      zh: 'Australia/Sydney (GMT+10:00) - 悉尼'
    }
  },
  {
    value: 'Australia/Melbourne',
    label: {
      en: 'Australia/Melbourne (GMT+10:00) - Melbourne',
      zh: 'Australia/Melbourne (GMT+10:00) - 墨尔本'
    }
  },
  {
    value: 'Pacific/Guam',
    label: {
      en: 'Pacific/Guam (GMT+10:00) - Guam',
      zh: 'Pacific/Guam (GMT+10:00) - 关岛'
    }
  },
  {
    value: 'Pacific/Fiji',
    label: {
      en: 'Pacific/Fiji (GMT+12:00) - Fiji',
      zh: 'Pacific/Fiji (GMT+12:00) - 斐济'
    }
  },
  {
    value: 'Pacific/Auckland',
    label: {
      en: 'Pacific/Auckland (GMT+12:00) - Auckland',
      zh: 'Pacific/Auckland (GMT+12:00) - 奥克兰'
    }
  }
]

// Get localized timezone list
export function getLocalizedTimezones(language = 'en') {
  const lang = language === 'zh-CN' ? 'zh' : language === 'es' ? 'es' : 'en'
  return COMMON_TIMEZONES.map((tz) => ({
    value: tz.value,
    label: typeof tz.label === 'string' ? tz.label : tz.label[lang]
  }))
}

export function getTimezoneOffset(timezone) {
  try {
    const now = new Date()
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      timeZoneName: 'longOffset'
    })

    const parts = formatter.formatToParts(now)
    const offsetPart = parts.find((part) => part.type === 'timeZoneName')

    if (offsetPart) {
      return offsetPart.value
    }

    const formatted = formatInTimeZone(now, timezone, 'XXX')
    return `GMT${formatted}`
  } catch (error) {
    return ''
  }
}

export function getTimezoneLabel(timezone) {
  const offset = getTimezoneOffset(timezone)
  return `${timezone} (${offset})`
}

export function getAllTimezones() {
  return COMMON_TIMEZONES
}

export function groupTimezonesByRegion() {
  return {
    Americas: COMMON_TIMEZONES.filter(
      (tz) =>
        tz.value.startsWith('America/') ||
        tz.value.startsWith('Pacific/Honolulu') ||
        tz.value.startsWith('Pacific/Midway')
    ),
    'Europe & Africa': COMMON_TIMEZONES.filter(
      (tz) =>
        tz.value.startsWith('Europe/') ||
        tz.value.startsWith('Atlantic/') ||
        tz.value.startsWith('Africa/')
    ),
    Asia: COMMON_TIMEZONES.filter((tz) => tz.value.startsWith('Asia/')),
    Pacific: COMMON_TIMEZONES.filter(
      (tz) =>
        tz.value.startsWith('Australia/') ||
        (tz.value.startsWith('Pacific/') &&
          !tz.value.includes('Honolulu') &&
          !tz.value.includes('Midway'))
    ),
    UTC: COMMON_TIMEZONES.filter((tz) => tz.value === 'UTC')
  }
}
