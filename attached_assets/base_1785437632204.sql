-- ============================================================================
-- Gallo — Esquema Postgres / Supabase
-- Fuente canónica del modelo de datos. Migración: supabase/migrations/
-- ============================================================================
-- Requisitos: Supabase Auth (auth.users). Ejecutar en SQL Editor o via CLI.
-- La app debe pasar { data: { name } } en signUp para poblar perfiles.nombre.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 0. EXTENSIONES
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1. PERFILES (Auth — Módulos 1–3)
-- ---------------------------------------------------------------------------
CREATE TABLE public.perfiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL PRIMARY KEY,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ---------------------------------------------------------------------------
-- 1.5 AMIGOS (Módulo 6)
-- ---------------------------------------------------------------------------
CREATE TABLE public.amigos (
    usuario_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    amigo_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    PRIMARY KEY (usuario_id, amigo_id),
    CHECK (usuario_id <> amigo_id)
);

-- ---------------------------------------------------------------------------
-- 2. MESAS DE TRABAJO (Módulo 4)
-- ---------------------------------------------------------------------------
CREATE TABLE public.mesas_trabajo (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creador_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ---------------------------------------------------------------------------
-- 3. CATÁLOGOS (Módulos 7.1.2 y 8.6)
-- ---------------------------------------------------------------------------
CREATE TABLE public.cat_tipos_comida (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO public.cat_tipos_comida (nombre)
VALUES ('Desayuno'), ('Comida'), ('Cena'), ('Otro');

CREATE TABLE public.lugares_compra (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creador_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ---------------------------------------------------------------------------
-- 4. PLATILLOS E INGREDIENTES (Módulo 7)
-- ---------------------------------------------------------------------------
CREATE TABLE public.platillos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creador_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE public.platillo_tipos (
    platillo_id UUID REFERENCES public.platillos(id) ON DELETE CASCADE NOT NULL,
    tipo_comida_id INT REFERENCES public.cat_tipos_comida(id) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (platillo_id, tipo_comida_id)
);

CREATE TABLE public.ingredientes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creador_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    nombre TEXT NOT NULL,
    categoria TEXT,
    stock TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE public.platillo_ingredientes (
    platillo_id UUID REFERENCES public.platillos(id) ON DELETE CASCADE NOT NULL,
    ingrediente_id UUID REFERENCES public.ingredientes(id) ON DELETE CASCADE NOT NULL,
    cantidad TEXT,
    PRIMARY KEY (platillo_id, ingrediente_id)
);

-- ---------------------------------------------------------------------------
-- 5. MENÚS Y COMPARTICIÓN (Módulo 5)
-- ---------------------------------------------------------------------------
CREATE TABLE public.menus (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mesa_trabajo_id UUID REFERENCES public.mesas_trabajo(id) ON DELETE CASCADE NOT NULL,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE public.menu_platillos (
    menu_id UUID REFERENCES public.menus(id) ON DELETE CASCADE NOT NULL,
    platillo_id UUID REFERENCES public.platillos(id) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (menu_id, platillo_id)
);

CREATE TABLE public.menu_compartido (
    menu_id UUID REFERENCES public.menus(id) ON DELETE CASCADE NOT NULL,
    usuario_invitado_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    PRIMARY KEY (menu_id, usuario_invitado_id),
    CONSTRAINT menu_compartido_estado_check
        CHECK (estado IN ('pendiente', 'aceptado', 'denegado'))
);

-- ---------------------------------------------------------------------------
-- 6. LISTAS DE COMPRAS (Módulo 8)
-- ---------------------------------------------------------------------------
CREATE TABLE public.listas_compras (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mesa_trabajo_id UUID REFERENCES public.mesas_trabajo(id) ON DELETE CASCADE NOT NULL,
    menu_id UUID UNIQUE NOT NULL REFERENCES public.menus(id) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE public.lista_compra_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    lista_compra_id UUID REFERENCES public.listas_compras(id) ON DELETE CASCADE NOT NULL,
    ingrediente_id UUID REFERENCES public.ingredientes(id) ON DELETE CASCADE NOT NULL,
    lugar_compra_id UUID REFERENCES public.lugares_compra(id) ON DELETE SET NULL,
    agregado_manualmente BOOLEAN DEFAULT FALSE NOT NULL,
    comprado BOOLEAN DEFAULT FALSE NOT NULL,
    orden INT DEFAULT 0 NOT NULL,
    UNIQUE (lista_compra_id, ingrediente_id)
);

CREATE TABLE public.lista_compra_item_platillos (
    lista_compra_item_id UUID REFERENCES public.lista_compra_items(id) ON DELETE CASCADE NOT NULL,
    platillo_id UUID REFERENCES public.platillos(id) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (lista_compra_item_id, platillo_id)
);

-- ---------------------------------------------------------------------------
-- 7. ENCUESTAS (Módulo 9)
-- ---------------------------------------------------------------------------
CREATE TABLE public.encuestas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    creador_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    titulo TEXT NOT NULL,
    estado VARCHAR(20) DEFAULT 'activa' NOT NULL,
    fecha_cierre TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT encuestas_estado_check CHECK (estado IN ('activa', 'cerrada'))
);

CREATE TABLE public.encuesta_compartida (
    encuesta_id UUID REFERENCES public.encuestas(id) ON DELETE CASCADE NOT NULL,
    usuario_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    PRIMARY KEY (encuesta_id, usuario_id),
    CONSTRAINT encuesta_compartida_estado_check
        CHECK (estado IN ('pendiente', 'aceptada', 'rechazada'))
);

CREATE TABLE public.encuesta_opciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    encuesta_id UUID REFERENCES public.encuestas(id) ON DELETE CASCADE NOT NULL,
    platillo_id UUID REFERENCES public.platillos(id) ON DELETE CASCADE NOT NULL
);

CREATE TABLE public.encuesta_votos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    encuesta_id UUID REFERENCES public.encuestas(id) ON DELETE CASCADE NOT NULL,
    encuesta_opcion_id UUID REFERENCES public.encuesta_opciones(id) ON DELETE CASCADE NOT NULL,
    usuario_id UUID REFERENCES public.perfiles(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE (encuesta_id, usuario_id)
);

-- ---------------------------------------------------------------------------
-- 8. ÍNDICES
-- ---------------------------------------------------------------------------
CREATE INDEX idx_mesas_creador ON public.mesas_trabajo(creador_id);
CREATE INDEX idx_menus_mesa ON public.menus(mesa_trabajo_id);
CREATE INDEX idx_menu_compartido_usuario ON public.menu_compartido(usuario_invitado_id, estado);
CREATE INDEX idx_platillos_creador ON public.platillos(creador_id);
CREATE INDEX idx_ingredientes_creador ON public.ingredientes(creador_id);
CREATE INDEX idx_lugares_creador ON public.lugares_compra(creador_id);
CREATE INDEX idx_lista_items_lista ON public.lista_compra_items(lista_compra_id);
CREATE INDEX idx_encuesta_votos_encuesta ON public.encuesta_votos(encuesta_id);
CREATE INDEX idx_encuesta_compartida_usuario ON public.encuesta_compartida(usuario_id, estado);
CREATE INDEX idx_perfiles_nombre ON public.perfiles(nombre);

-- ---------------------------------------------------------------------------
-- 9. HELPERS DE ACCESO (RLS)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_mesa(p_mesa_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.mesas_trabajo mt
        WHERE mt.id = p_mesa_id AND mt.creador_id = auth.uid()
    ) OR EXISTS (
        SELECT 1
        FROM public.menus m
        JOIN public.menu_compartido mc ON mc.menu_id = m.id
        WHERE m.mesa_trabajo_id = p_mesa_id
          AND mc.usuario_invitado_id = auth.uid()
          AND mc.estado = 'aceptado'
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_menu(p_menu_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.menus m
        JOIN public.mesas_trabajo mt ON mt.id = m.mesa_trabajo_id
        WHERE m.id = p_menu_id AND mt.creador_id = auth.uid()
    ) OR EXISTS (
        SELECT 1 FROM public.menu_compartido mc
        WHERE mc.menu_id = p_menu_id
          AND mc.usuario_invitado_id = auth.uid()
          AND mc.estado = 'aceptado'
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_es_dueño_mesa_por_menu(p_menu_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.menus m
        JOIN public.mesas_trabajo mt ON mt.id = m.mesa_trabajo_id
        WHERE m.id = p_menu_id AND mt.creador_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_encuesta(p_encuesta_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.encuestas e
        WHERE e.id = p_encuesta_id AND e.creador_id = auth.uid()
    ) OR EXISTS (
        SELECT 1 FROM public.encuesta_compartida ec
        WHERE ec.encuesta_id = p_encuesta_id
          AND ec.usuario_id = auth.uid()
          AND ec.estado = 'aceptada'
    );
$$;

-- ---------------------------------------------------------------------------
-- 10. HELPERS INTERNOS — LISTAS DE COMPRAS
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fn_upsert_item_lista_platillo(
    p_lista_id UUID,
    p_ingrediente_id UUID,
    p_platillo_id UUID
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_item_id UUID;
BEGIN
    INSERT INTO public.lista_compra_items (lista_compra_id, ingrediente_id)
    VALUES (p_lista_id, p_ingrediente_id)
    ON CONFLICT (lista_compra_id, ingrediente_id) DO NOTHING;

    SELECT id INTO v_item_id
    FROM public.lista_compra_items
    WHERE lista_compra_id = p_lista_id AND ingrediente_id = p_ingrediente_id;

    IF v_item_id IS NOT NULL THEN
        INSERT INTO public.lista_compra_item_platillos (lista_compra_item_id, platillo_id)
        VALUES (v_item_id, p_platillo_id)
        ON CONFLICT DO NOTHING;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION public.fn_limpiar_items_huerfanos_lista(p_lista_id UUID)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    DELETE FROM public.lista_compra_items lci
    WHERE lci.lista_compra_id = p_lista_id
      AND lci.agregado_manualmente = FALSE
      AND NOT EXISTS (
          SELECT 1 FROM public.lista_compra_item_platillos p
          WHERE p.lista_compra_item_id = lci.id
      );
END;
$$;

-- ---------------------------------------------------------------------------
-- 11. TRIGGERS — AUTH (signup → perfil)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.perfiles (id, nombre)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ---------------------------------------------------------------------------
-- 12. TRIGGERS — LISTAS DE COMPRAS (Módulo 8)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fn_crear_lista_compras()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.listas_compras (mesa_trabajo_id, menu_id, nombre)
    VALUES (NEW.mesa_trabajo_id, NEW.id, 'Lista de compras — ' || NEW.nombre);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_crear_lista_compras
    AFTER INSERT ON public.menus
    FOR EACH ROW EXECUTE FUNCTION public.fn_crear_lista_compras();

CREATE OR REPLACE FUNCTION public.fn_sync_lista_platillo_add()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_lista_id UUID;
    ing RECORD;
BEGIN
    SELECT id INTO v_lista_id FROM public.listas_compras WHERE menu_id = NEW.menu_id;
    IF v_lista_id IS NULL THEN RETURN NEW; END IF;

    FOR ing IN
        SELECT ingrediente_id FROM public.platillo_ingredientes WHERE platillo_id = NEW.platillo_id
    LOOP
        PERFORM public.fn_upsert_item_lista_platillo(v_lista_id, ing.ingrediente_id, NEW.platillo_id);
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_lista_platillo_add
    AFTER INSERT ON public.menu_platillos
    FOR EACH ROW EXECUTE FUNCTION public.fn_sync_lista_platillo_add();

CREATE OR REPLACE FUNCTION public.fn_sync_lista_platillo_remove()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_lista_id UUID;
BEGIN
    SELECT id INTO v_lista_id FROM public.listas_compras WHERE menu_id = OLD.menu_id;
    IF v_lista_id IS NULL THEN RETURN OLD; END IF;

    DELETE FROM public.lista_compra_item_platillos
    WHERE platillo_id = OLD.platillo_id
      AND lista_compra_item_id IN (
          SELECT id FROM public.lista_compra_items WHERE lista_compra_id = v_lista_id
      );

    PERFORM public.fn_limpiar_items_huerfanos_lista(v_lista_id);
    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_sync_lista_platillo_remove
    AFTER DELETE ON public.menu_platillos
    FOR EACH ROW EXECUTE FUNCTION public.fn_sync_lista_platillo_remove();

CREATE OR REPLACE FUNCTION public.fn_sync_lista_platillo_ingrediente_add()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    rec_menu RECORD;
    v_lista_id UUID;
BEGIN
    FOR rec_menu IN
        SELECT menu_id FROM public.menu_platillos WHERE platillo_id = NEW.platillo_id
    LOOP
        SELECT id INTO v_lista_id FROM public.listas_compras WHERE menu_id = rec_menu.menu_id;
        IF v_lista_id IS NOT NULL THEN
            PERFORM public.fn_upsert_item_lista_platillo(v_lista_id, NEW.ingrediente_id, NEW.platillo_id);
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_sync_lista_platillo_ingrediente_add
    AFTER INSERT ON public.platillo_ingredientes
    FOR EACH ROW EXECUTE FUNCTION public.fn_sync_lista_platillo_ingrediente_add();

CREATE OR REPLACE FUNCTION public.fn_sync_lista_platillo_ingrediente_remove()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    rec_menu RECORD;
    v_lista_id UUID;
    v_item_id UUID;
BEGIN
    FOR rec_menu IN
        SELECT menu_id FROM public.menu_platillos WHERE platillo_id = OLD.platillo_id
    LOOP
        SELECT id INTO v_lista_id FROM public.listas_compras WHERE menu_id = rec_menu.menu_id;
        IF v_lista_id IS NULL THEN CONTINUE; END IF;

        SELECT lci.id INTO v_item_id
        FROM public.lista_compra_items lci
        WHERE lci.lista_compra_id = v_lista_id AND lci.ingrediente_id = OLD.ingrediente_id;

        IF v_item_id IS NULL THEN CONTINUE; END IF;

        DELETE FROM public.lista_compra_item_platillos
        WHERE lista_compra_item_id = v_item_id AND platillo_id = OLD.platillo_id;

        PERFORM public.fn_limpiar_items_huerfanos_lista(v_lista_id);
    END LOOP;
    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_sync_lista_platillo_ingrediente_remove
    AFTER DELETE ON public.platillo_ingredientes
    FOR EACH ROW EXECUTE FUNCTION public.fn_sync_lista_platillo_ingrediente_remove();

-- ---------------------------------------------------------------------------
-- 13. TRIGGERS — AMIGOS AUTO (Módulo 6.3)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.fn_auto_amistad(p_usuario_a UUID, p_usuario_b UUID)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    IF p_usuario_a IS NULL OR p_usuario_b IS NULL OR p_usuario_a = p_usuario_b THEN
        RETURN;
    END IF;
    INSERT INTO public.amigos (usuario_id, amigo_id)
    VALUES (p_usuario_a, p_usuario_b), (p_usuario_b, p_usuario_a)
    ON CONFLICT DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION public.fn_auto_amistad_menu_compartido()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_creador UUID;
BEGIN
    SELECT mt.creador_id INTO v_creador
    FROM public.menus m
    JOIN public.mesas_trabajo mt ON mt.id = m.mesa_trabajo_id
    WHERE m.id = NEW.menu_id;

    PERFORM public.fn_auto_amistad(v_creador, NEW.usuario_invitado_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_auto_amistad_menu_compartido
    AFTER INSERT ON public.menu_compartido
    FOR EACH ROW EXECUTE FUNCTION public.fn_auto_amistad_menu_compartido();

CREATE OR REPLACE FUNCTION public.fn_auto_amistad_encuesta_compartida()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_creador UUID;
BEGIN
    SELECT creador_id INTO v_creador FROM public.encuestas WHERE id = NEW.encuesta_id;
    PERFORM public.fn_auto_amistad(v_creador, NEW.usuario_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_auto_amistad_encuesta_compartida
    AFTER INSERT ON public.encuesta_compartida
    FOR EACH ROW EXECUTE FUNCTION public.fn_auto_amistad_encuesta_compartida();

-- ---------------------------------------------------------------------------
-- 14. RPC — AMIGOS (Módulo 6)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.agregar_amigo(p_amigo_id UUID)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No autenticado';
    END IF;
    IF p_amigo_id = auth.uid() THEN
        RAISE EXCEPTION 'No puedes agregarte a ti mismo';
    END IF;
    PERFORM public.fn_auto_amistad(auth.uid(), p_amigo_id);
END;
$$;

GRANT EXECUTE ON FUNCTION public.agregar_amigo(UUID) TO authenticated;

-- ---------------------------------------------------------------------------
-- 15. ROW LEVEL SECURITY
-- ---------------------------------------------------------------------------
ALTER TABLE public.perfiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amigos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mesas_trabajo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cat_tipos_comida ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lugares_compra ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platillos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platillo_tipos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingredientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platillo_ingredientes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menus ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menu_platillos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.menu_compartido ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listas_compras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lista_compra_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lista_compra_item_platillos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encuestas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encuesta_compartida ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encuesta_opciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encuesta_votos ENABLE ROW LEVEL SECURITY;

-- perfiles
CREATE POLICY perfiles_select ON public.perfiles FOR SELECT TO authenticated USING (true);
CREATE POLICY perfiles_update ON public.perfiles FOR UPDATE TO authenticated
    USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- amigos
CREATE POLICY amigos_select ON public.amigos FOR SELECT TO authenticated
    USING (usuario_id = auth.uid());

-- mesas_trabajo
CREATE POLICY mesas_select ON public.mesas_trabajo FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_mesa(id));
CREATE POLICY mesas_insert ON public.mesas_trabajo FOR INSERT TO authenticated
    WITH CHECK (creador_id = auth.uid());
CREATE POLICY mesas_update ON public.mesas_trabajo FOR UPDATE TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());
CREATE POLICY mesas_delete ON public.mesas_trabajo FOR DELETE TO authenticated
    USING (creador_id = auth.uid());

-- cat_tipos_comida (solo lectura)
CREATE POLICY cat_tipos_select ON public.cat_tipos_comida FOR SELECT TO authenticated USING (true);

-- lugares_compra
CREATE POLICY lugares_all ON public.lugares_compra FOR ALL TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());

-- platillos
CREATE POLICY platillos_all ON public.platillos FOR ALL TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());

CREATE POLICY platillo_tipos_all ON public.platillo_tipos FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.platillos p
        WHERE p.id = platillo_id AND p.creador_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.platillos p
        WHERE p.id = platillo_id AND p.creador_id = auth.uid()
    ));

-- ingredientes
CREATE POLICY ingredientes_all ON public.ingredientes FOR ALL TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());

CREATE POLICY platillo_ingredientes_all ON public.platillo_ingredientes FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.platillos p
        WHERE p.id = platillo_id AND p.creador_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.platillos p
        WHERE p.id = platillo_id AND p.creador_id = auth.uid()
    ));

-- menus
CREATE POLICY menus_select ON public.menus FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_menu(id));
CREATE POLICY menus_insert ON public.menus FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.mesas_trabajo mt
        WHERE mt.id = mesa_trabajo_id AND mt.creador_id = auth.uid()
    ));
CREATE POLICY menus_update ON public.menus FOR UPDATE TO authenticated
    USING (public.usuario_es_dueño_mesa_por_menu(id))
    WITH CHECK (public.usuario_es_dueño_mesa_por_menu(id));
CREATE POLICY menus_delete ON public.menus FOR DELETE TO authenticated
    USING (public.usuario_es_dueño_mesa_por_menu(id));

CREATE POLICY menu_platillos_select ON public.menu_platillos FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_menu(menu_id));
CREATE POLICY menu_platillos_mutate ON public.menu_platillos FOR ALL TO authenticated
    USING (public.usuario_es_dueño_mesa_por_menu(menu_id))
    WITH CHECK (public.usuario_es_dueño_mesa_por_menu(menu_id));

-- menu_compartido
CREATE POLICY menu_compartido_select ON public.menu_compartido FOR SELECT TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_dueño_mesa_por_menu(menu_id)
    );
CREATE POLICY menu_compartido_insert ON public.menu_compartido FOR INSERT TO authenticated
    WITH CHECK (public.usuario_es_dueño_mesa_por_menu(menu_id));
CREATE POLICY menu_compartido_update ON public.menu_compartido FOR UPDATE TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_dueño_mesa_por_menu(menu_id)
    )
    WITH CHECK (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_dueño_mesa_por_menu(menu_id)
    );
CREATE POLICY menu_compartido_delete ON public.menu_compartido FOR DELETE TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_dueño_mesa_por_menu(menu_id)
    );

-- listas de compras
CREATE POLICY listas_select ON public.listas_compras FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_menu(menu_id));
CREATE POLICY listas_update ON public.listas_compras FOR UPDATE TO authenticated
    USING (public.usuario_tiene_acceso_menu(menu_id))
    WITH CHECK (public.usuario_tiene_acceso_menu(menu_id));

CREATE POLICY lista_items_select ON public.lista_compra_items FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.listas_compras lc
        WHERE lc.id = lista_compra_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ));
CREATE POLICY lista_items_mutate ON public.lista_compra_items FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.listas_compras lc
        WHERE lc.id = lista_compra_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.listas_compras lc
        WHERE lc.id = lista_compra_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ));

CREATE POLICY lista_item_platillos_select ON public.lista_compra_item_platillos FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.lista_compra_items lci
        JOIN public.listas_compras lc ON lc.id = lci.lista_compra_id
        WHERE lci.id = lista_compra_item_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ));
CREATE POLICY lista_item_platillos_mutate ON public.lista_compra_item_platillos FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.lista_compra_items lci
        JOIN public.listas_compras lc ON lc.id = lci.lista_compra_id
        WHERE lci.id = lista_compra_item_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.lista_compra_items lci
        JOIN public.listas_compras lc ON lc.id = lci.lista_compra_id
        WHERE lci.id = lista_compra_item_id AND public.usuario_tiene_acceso_menu(lc.menu_id)
    ));

-- encuestas
CREATE POLICY encuestas_select ON public.encuestas FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_encuesta(id));
CREATE POLICY encuestas_mutate ON public.encuestas FOR ALL TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());

CREATE POLICY encuesta_compartida_select ON public.encuesta_compartida FOR SELECT TO authenticated
    USING (
        usuario_id = auth.uid()
        OR EXISTS (SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid())
    );
CREATE POLICY encuesta_compartida_insert ON public.encuesta_compartida FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid()
    ));
CREATE POLICY encuesta_compartida_update ON public.encuesta_compartida FOR UPDATE TO authenticated
    USING (
        usuario_id = auth.uid()
        OR EXISTS (SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid())
    )
    WITH CHECK (
        usuario_id = auth.uid()
        OR EXISTS (SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid())
    );
CREATE POLICY encuesta_compartida_delete ON public.encuesta_compartida FOR DELETE TO authenticated
    USING (
        usuario_id = auth.uid()
        OR EXISTS (SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid())
    );

CREATE POLICY encuesta_opciones_select ON public.encuesta_opciones FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_encuesta(encuesta_id));
CREATE POLICY encuesta_opciones_mutate ON public.encuesta_opciones FOR ALL TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.encuestas e WHERE e.id = encuesta_id AND e.creador_id = auth.uid()
    ));

CREATE POLICY encuesta_votos_select ON public.encuesta_votos FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_encuesta(encuesta_id));
CREATE POLICY encuesta_votos_insert ON public.encuesta_votos FOR INSERT TO authenticated
    WITH CHECK (
        usuario_id = auth.uid()
        AND public.usuario_tiene_acceso_encuesta(encuesta_id)
    );
CREATE POLICY encuesta_votos_update ON public.encuesta_votos FOR UPDATE TO authenticated
    USING (usuario_id = auth.uid()) WITH CHECK (usuario_id = auth.uid());
CREATE POLICY encuesta_votos_delete ON public.encuesta_votos FOR DELETE TO authenticated
    USING (usuario_id = auth.uid());

-- ---------------------------------------------------------------------------
-- 16. RPC DE NEGOCIO (endpoints compuestos — Docs/backend-endpoints-prompt.md)
-- ---------------------------------------------------------------------------

-- 7.6 — Borrar platillo y opcionalmente ingredientes huérfanos seleccionados
CREATE OR REPLACE FUNCTION public.delete_platillo(
    p_platillo_id UUID,
    p_ingrediente_ids_a_borrar UUID[] DEFAULT ARRAY[]::UUID[]
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_ing UUID;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No autenticado';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.platillos
        WHERE id = p_platillo_id AND creador_id = auth.uid()
    ) THEN
        RAISE EXCEPTION 'Platillo no encontrado o sin permiso';
    END IF;

    DELETE FROM public.platillos WHERE id = p_platillo_id;

    IF p_ingrediente_ids_a_borrar IS NOT NULL THEN
        FOREACH v_ing IN ARRAY p_ingrediente_ids_a_borrar
        LOOP
            IF EXISTS (
                SELECT 1 FROM public.ingredientes i
                WHERE i.id = v_ing
                  AND i.creador_id = auth.uid()
                  AND NOT EXISTS (
                      SELECT 1 FROM public.platillo_ingredientes pi
                      WHERE pi.ingrediente_id = v_ing
                  )
            ) THEN
                DELETE FROM public.ingredientes WHERE id = v_ing;
            END IF;
        END LOOP;
    END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION public.delete_platillo(UUID, UUID[]) TO authenticated;

-- 8.12 — Asignar item de lista a platillo existente
CREATE OR REPLACE FUNCTION public.assign_lista_item_platillo(
    p_item_id UUID,
    p_platillo_id UUID
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_ingrediente_id UUID;
    v_lista_id UUID;
    v_menu_id UUID;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No autenticado';
    END IF;

    SELECT lci.ingrediente_id, lci.lista_compra_id
      INTO v_ingrediente_id, v_lista_id
    FROM public.lista_compra_items lci
    WHERE lci.id = p_item_id;

    IF v_ingrediente_id IS NULL THEN
        RAISE EXCEPTION 'Item de lista no encontrado';
    END IF;

    SELECT lc.menu_id INTO v_menu_id
    FROM public.listas_compras lc
    WHERE lc.id = v_lista_id;

    IF NOT public.usuario_tiene_acceso_menu(v_menu_id) THEN
        RAISE EXCEPTION 'Sin acceso a la lista de compras';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.platillos
        WHERE id = p_platillo_id AND creador_id = auth.uid()
    ) THEN
        RAISE EXCEPTION 'Platillo no encontrado o sin permiso';
    END IF;

    INSERT INTO public.platillo_ingredientes (platillo_id, ingrediente_id)
    VALUES (p_platillo_id, v_ingrediente_id)
    ON CONFLICT DO NOTHING;

    INSERT INTO public.lista_compra_item_platillos (lista_compra_item_id, platillo_id)
    VALUES (p_item_id, p_platillo_id)
    ON CONFLICT DO NOTHING;
END;
$$;

GRANT EXECUTE ON FUNCTION public.assign_lista_item_platillo(UUID, UUID) TO authenticated;

-- 8.12 — Crear platillo nuevo y asignar item de lista
CREATE OR REPLACE FUNCTION public.assign_lista_item_platillo_nuevo(
    p_item_id UUID,
    p_nombre TEXT,
    p_tipos TEXT[] DEFAULT ARRAY[]::TEXT[]
)
RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_platillo_id UUID;
    v_tipo TEXT;
    v_tipo_id INT;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No autenticado';
    END IF;

    IF p_nombre IS NULL OR btrim(p_nombre) = '' THEN
        RAISE EXCEPTION 'Nombre de platillo requerido';
    END IF;

    INSERT INTO public.platillos (creador_id, nombre)
    VALUES (auth.uid(), btrim(p_nombre))
    RETURNING id INTO v_platillo_id;

    IF p_tipos IS NOT NULL THEN
        FOREACH v_tipo IN ARRAY p_tipos
        LOOP
            SELECT id INTO v_tipo_id
            FROM public.cat_tipos_comida
            WHERE lower(nombre) = lower(v_tipo);

            IF v_tipo_id IS NOT NULL THEN
                INSERT INTO public.platillo_tipos (platillo_id, tipo_comida_id)
                VALUES (v_platillo_id, v_tipo_id)
                ON CONFLICT DO NOTHING;
            END IF;
        END LOOP;
    END IF;

    PERFORM public.assign_lista_item_platillo(p_item_id, v_platillo_id);
    RETURN v_platillo_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.assign_lista_item_platillo_nuevo(UUID, TEXT, TEXT[]) TO authenticated;

-- 9 — Votar / toggle / cambiar voto (1 por usuario por encuesta)
CREATE OR REPLACE FUNCTION public.votar_encuesta(
    p_encuesta_id UUID,
    p_opcion_id UUID
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
    v_voto_existente UUID;
    v_opcion_actual UUID;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'No autenticado';
    END IF;

    IF NOT public.usuario_tiene_acceso_encuesta(p_encuesta_id) THEN
        RAISE EXCEPTION 'Sin acceso a la encuesta';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.encuestas
        WHERE id = p_encuesta_id AND estado = 'activa'
    ) THEN
        RAISE EXCEPTION 'La encuesta no está activa';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.encuesta_opciones
        WHERE id = p_opcion_id AND encuesta_id = p_encuesta_id
    ) THEN
        RAISE EXCEPTION 'Opción inválida para esta encuesta';
    END IF;

    SELECT id, encuesta_opcion_id
      INTO v_voto_existente, v_opcion_actual
    FROM public.encuesta_votos
    WHERE encuesta_id = p_encuesta_id AND usuario_id = auth.uid();

    IF v_voto_existente IS NOT NULL AND v_opcion_actual = p_opcion_id THEN
        DELETE FROM public.encuesta_votos WHERE id = v_voto_existente;
        RETURN;
    END IF;

    IF v_voto_existente IS NOT NULL THEN
        UPDATE public.encuesta_votos
        SET encuesta_opcion_id = p_opcion_id
        WHERE id = v_voto_existente;
        RETURN;
    END IF;

    INSERT INTO public.encuesta_votos (encuesta_id, encuesta_opcion_id, usuario_id)
    VALUES (p_encuesta_id, p_opcion_id, auth.uid());
END;
$$;

GRANT EXECUTE ON FUNCTION public.votar_encuesta(UUID, UUID) TO authenticated;

-- ---------------------------------------------------------------------------
-- 17. GRANTS
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT SELECT ON public.cat_tipos_comida TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
