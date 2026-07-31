-- 1. Actualizar Funciones Helper (usar CREATE OR REPLACE)
CREATE OR REPLACE FUNCTION public.usuario_es_creador_mesa(p_mesa_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.mesas_trabajo mt
        WHERE mt.id = p_mesa_id AND mt.creador_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_es_invitado_mesa(p_mesa_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.menus m
        JOIN public.menu_compartido mc ON mc.menu_id = m.id
        WHERE m.mesa_trabajo_id = p_mesa_id
          AND mc.usuario_invitado_id = auth.uid()
          AND mc.estado = 'aceptado'
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_mesa(p_mesa_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT public.usuario_es_creador_mesa(p_mesa_id) OR public.usuario_es_invitado_mesa(p_mesa_id);
$$;

CREATE OR REPLACE FUNCTION public.usuario_es_creador_mesa_por_menu(p_menu_id UUID)
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

CREATE OR REPLACE FUNCTION public.usuario_es_invitado_menu(p_menu_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.menu_compartido mc
        WHERE mc.menu_id = p_menu_id
          AND mc.usuario_invitado_id = auth.uid()
          AND mc.estado = 'aceptado'
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_menu(p_menu_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT public.usuario_es_creador_mesa_por_menu(p_menu_id) OR public.usuario_es_invitado_menu(p_menu_id);
$$;

CREATE OR REPLACE FUNCTION public.usuario_es_creador_encuesta(p_encuesta_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.encuestas e
        WHERE e.id = p_encuesta_id AND e.creador_id = auth.uid()
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_es_invitado_encuesta(p_encuesta_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.encuesta_compartida ec
        WHERE ec.encuesta_id = p_encuesta_id
          AND ec.usuario_id = auth.uid()
          AND ec.estado = 'aceptada'
    );
$$;

CREATE OR REPLACE FUNCTION public.usuario_tiene_acceso_encuesta(p_encuesta_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
    SELECT public.usuario_es_creador_encuesta(p_encuesta_id) OR public.usuario_es_invitado_encuesta(p_encuesta_id);
$$;

-- Nota: Ya no usamos `usuario_es_dueño_mesa_por_menu`, puedes borrarla si quieres:
DROP FUNCTION IF EXISTS public.usuario_es_dueño_mesa_por_menu(UUID);

-- 2. Eliminar Políticas Viejas y Crear las Nuevas Optimizadas

-- mesas_trabajo
DROP POLICY IF EXISTS mesas_select ON public.mesas_trabajo;
DROP POLICY IF EXISTS mesas_insert ON public.mesas_trabajo;
DROP POLICY IF EXISTS mesas_update ON public.mesas_trabajo;
DROP POLICY IF EXISTS mesas_delete ON public.mesas_trabajo;

CREATE POLICY mesas_select ON public.mesas_trabajo FOR SELECT TO authenticated
    USING (creador_id = auth.uid() OR public.usuario_es_invitado_mesa(id));
CREATE POLICY mesas_insert ON public.mesas_trabajo FOR INSERT TO authenticated
    WITH CHECK (creador_id = auth.uid());
CREATE POLICY mesas_update ON public.mesas_trabajo FOR UPDATE TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());
CREATE POLICY mesas_delete ON public.mesas_trabajo FOR DELETE TO authenticated
    USING (creador_id = auth.uid());

-- menus
DROP POLICY IF EXISTS menus_select ON public.menus;
DROP POLICY IF EXISTS menus_insert ON public.menus;
DROP POLICY IF EXISTS menus_update ON public.menus;
DROP POLICY IF EXISTS menus_delete ON public.menus;

CREATE POLICY menus_select ON public.menus FOR SELECT TO authenticated
    USING (public.usuario_es_creador_mesa(mesa_trabajo_id) OR public.usuario_es_invitado_menu(id));
CREATE POLICY menus_insert ON public.menus FOR INSERT TO authenticated
    WITH CHECK (public.usuario_es_creador_mesa(mesa_trabajo_id));
CREATE POLICY menus_update ON public.menus FOR UPDATE TO authenticated
    USING (public.usuario_es_creador_mesa(mesa_trabajo_id))
    WITH CHECK (public.usuario_es_creador_mesa(mesa_trabajo_id));
CREATE POLICY menus_delete ON public.menus FOR DELETE TO authenticated
    USING (public.usuario_es_creador_mesa(mesa_trabajo_id));

-- menu_platillos
DROP POLICY IF EXISTS menu_platillos_select ON public.menu_platillos;
DROP POLICY IF EXISTS menu_platillos_mutate ON public.menu_platillos;

CREATE POLICY menu_platillos_select ON public.menu_platillos FOR SELECT TO authenticated
    USING (public.usuario_tiene_acceso_menu(menu_id));
CREATE POLICY menu_platillos_mutate ON public.menu_platillos FOR ALL TO authenticated
    USING (public.usuario_es_creador_mesa_por_menu(menu_id))
    WITH CHECK (public.usuario_es_creador_mesa_por_menu(menu_id));

-- menu_compartido
DROP POLICY IF EXISTS menu_compartido_select ON public.menu_compartido;
DROP POLICY IF EXISTS menu_compartido_insert ON public.menu_compartido;
DROP POLICY IF EXISTS menu_compartido_update ON public.menu_compartido;
DROP POLICY IF EXISTS menu_compartido_delete ON public.menu_compartido;

CREATE POLICY menu_compartido_select ON public.menu_compartido FOR SELECT TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_creador_mesa_por_menu(menu_id)
    );
CREATE POLICY menu_compartido_insert ON public.menu_compartido FOR INSERT TO authenticated
    WITH CHECK (public.usuario_es_creador_mesa_por_menu(menu_id));
CREATE POLICY menu_compartido_update ON public.menu_compartido FOR UPDATE TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_creador_mesa_por_menu(menu_id)
    )
    WITH CHECK (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_creador_mesa_por_menu(menu_id)
    );
CREATE POLICY menu_compartido_delete ON public.menu_compartido FOR DELETE TO authenticated
    USING (
        usuario_invitado_id = auth.uid()
        OR public.usuario_es_creador_mesa_por_menu(menu_id)
    );

-- encuestas
DROP POLICY IF EXISTS encuestas_select ON public.encuestas;
DROP POLICY IF EXISTS encuestas_mutate ON public.encuestas;

CREATE POLICY encuestas_select ON public.encuestas FOR SELECT TO authenticated
    USING (creador_id = auth.uid() OR public.usuario_es_invitado_encuesta(id));
CREATE POLICY encuestas_mutate ON public.encuestas FOR ALL TO authenticated
    USING (creador_id = auth.uid()) WITH CHECK (creador_id = auth.uid());

-- encuesta_compartida
DROP POLICY IF EXISTS encuesta_compartida_select ON public.encuesta_compartida;
DROP POLICY IF EXISTS encuesta_compartida_insert ON public.encuesta_compartida;
DROP POLICY IF EXISTS encuesta_compartida_update ON public.encuesta_compartida;
DROP POLICY IF EXISTS encuesta_compartida_delete ON public.encuesta_compartida;

CREATE POLICY encuesta_compartida_select ON public.encuesta_compartida FOR SELECT TO authenticated
    USING (
        usuario_id = auth.uid()
        OR public.usuario_es_creador_encuesta(encuesta_id)
    );
CREATE POLICY encuesta_compartida_insert ON public.encuesta_compartida FOR INSERT TO authenticated
    WITH CHECK (public.usuario_es_creador_encuesta(encuesta_id));
CREATE POLICY encuesta_compartida_update ON public.encuesta_compartida FOR UPDATE TO authenticated
    USING (
        usuario_id = auth.uid()
        OR public.usuario_es_creador_encuesta(encuesta_id)
    )
    WITH CHECK (
        usuario_id = auth.uid()
        OR public.usuario_es_creador_encuesta(encuesta_id)
    );
CREATE POLICY encuesta_compartida_delete ON public.encuesta_compartida FOR DELETE TO authenticated
    USING (
        usuario_id = auth.uid()
        OR public.usuario_es_creador_encuesta(encuesta_id)
    );
