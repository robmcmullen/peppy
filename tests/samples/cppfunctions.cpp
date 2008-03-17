float TestClass::test1a(float arg) 
{
    printf("blah");
}


float TestClass::test1b(const float arg) 
{
    printf("blah");
}


float TestClass::test1c(const float arg) const
{
    printf("blah");
}


float TestClass::test1c(const float& arg) const
{
    printf("blah");
}


//After comments
float TestClass::test2a(const float& arg)
{
    printf("blah");
}

// this is commented_out (should not appear)
float TestClass::test2b(const float& arg) const
{
    printf("blah");
    if blah
}

/*
 * this is commented_out (should not appear)
 */
float TestClass::test2c(const float& arg) const
{
    printf("blah");
}

float* TestClass::test3a(const float& arg)
{
    printf("blah");
}

float* TestClass::test3b(const float& arg) const
{
    printf("blah");
}


int32_t TestClass::test4a(float arg)
{
    printf("blah");
}

int32_t* TestClass::test4b(const float& arg) const
{
    printf("blah");
}

