-- Логины пользователей по активным сессиям в Redis.
-- Сессия хранится как session:<uuid> -> {"user_id": 7, "login": "builder_lr4"}.
-- Результат: строки вида "builder_lr4 85727", где число - оставшееся время жизни сессии в секундах.
-- ARGV[1] - шаблон ключей сессий (необязательный, по умолчанию session:*)

local result = {}
local keys = redis.call('KEYS', ARGV[1] or 'session:*')
for i = 1, #keys do
    local value = redis.call('GET', keys[i])
    if value then
        local session = cjson.decode(value)
        local ttl = redis.call('TTL', keys[i])
        table.insert(result, session['login'] .. ' ' .. ttl)
    end
end
table.sort(result)
return result
