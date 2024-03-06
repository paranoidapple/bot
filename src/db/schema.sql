DO $$
BEGIN
    -- Create/alter swear counter
    IF NOT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = 'swear_counter') THEN
        CREATE TABLE IF NOT EXISTS swear_counter (
        user_id BIGINT,
        guild_id BIGINT,
        swears JSONB,
        UNIQUE (user_id, guild_id)
    );
    ELSE
        -- Add columns, honestly if I were to stop using a column I just wouldn't update it
        ALTER TABLE swear_counter
            ADD COLUMN IF NOT EXISTS user_id BIGINT,
            ADD COLUMN IF NOT EXISTS user_id BIGINT,
            ADD COLUMN IF NOT EXISTS swears JSONB,
            ADD UNIQUE (user_id, guild_id);
    END IF;


    -- Create/alter tags
    IF NOT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = 'tags') THEN
        CREATE TABLE IF NOT EXISTS tags (
        guild_id BIGINT,
        name TEXT,
        content TEXT,
        UNIQUE (name)
    );
    ELSE
        ALTER TABLE tags
        ADD COLUMN IF NOT EXISTS guild_id BIGINT,
        ADD COLUMN IF NOT EXISTS name TEXT,
        ADD COLUMN IF NOT EXISTS content TEXT,
        ADD UNIQUE (name);

         -- Drop old columns "key" and "value"
        IF EXISTS (SELECT column_name FROM information_schema.columns WHERE table_name = 'tags' AND column_name = 'key') THEN
            EXECUTE 'ALTER TABLE tags DROP COLUMN key';
        END IF;
        IF EXISTS (SELECT column_name FROM information_schema.columns WHERE table_name = 'tags' AND column_name = 'value') THEN
            EXECUTE 'ALTER TABLE tags DROP COLUMN value';
        END IF;
    END IF;


    -- Create/alter badges
    IF NOT EXISTS (SELECT * FROM information_schema.tables WHERE table_name = 'badges') THEN
        CREATE TABLE IF NOT EXISTS badges (
        name TEXT,
        description TEXT,
        guild_id BIGINT,
        badge_type TEXT,
        emoji TEXT,
        UNIQUE (name, guild_id)
    );
    ELSE
        ALTER TABLE badges
        ADD COLUMN IF NOT EXISTS name TEXT,
        ADD COLUMN IF NOT EXISTS description TEXT,
        ADD COLUMN IF NOT EXISTS guild_id BIGINT,
        ADD COLUMN IF NOT EXISTS badge_type TEXT,
        ADD COLUMN IF NOT EXISTS emoji TEXT,
        ADD UNIQUE (name, guild_id);
    END IF;
END $$;
