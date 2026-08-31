SET NOCOUNT ON;

IF DB_ID(N'DestekTakip') IS NULL
BEGIN
    CREATE DATABASE [DestekTakip];
END;
GO

DECLARE @app_password nvarchar(128) = N'$(APP_DATABASE_PASSWORD)';
DECLARE @login_statement nvarchar(max);

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE [name] = N'destek_app')
BEGIN
    SET @login_statement =
        N'CREATE LOGIN [destek_app] WITH PASSWORD = '
        + QUOTENAME(@app_password, N'''')
        + N', CHECK_POLICY = ON, CHECK_EXPIRATION = OFF;';
END;
ELSE
BEGIN
    SET @login_statement =
        N'ALTER LOGIN [destek_app] WITH PASSWORD = '
        + QUOTENAME(@app_password, N'''')
        + N';';
END;

EXEC sys.sp_executesql @login_statement;
GO

USE [DestekTakip];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE [name] = N'destek_app')
BEGIN
    CREATE USER [destek_app] FOR LOGIN [destek_app];
END;
ELSE
BEGIN
    ALTER USER [destek_app] WITH LOGIN = [destek_app];
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_role_members AS drm
    INNER JOIN sys.database_principals AS role_principal
        ON role_principal.principal_id = drm.role_principal_id
    INNER JOIN sys.database_principals AS member_principal
        ON member_principal.principal_id = drm.member_principal_id
    WHERE role_principal.[name] = N'db_owner'
      AND member_principal.[name] = N'destek_app'
)
BEGIN
    ALTER ROLE [db_owner] ADD MEMBER [destek_app];
END;
GO
